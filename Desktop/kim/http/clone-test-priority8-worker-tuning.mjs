#!/usr/bin/env node

import { Worker } from 'worker_threads';
import os from 'os';
import http from 'http';
import path from 'path';
import { fileURLToPath } from 'url';

/**
 * Clone Test Engine - Priority 8: Worker Tuning Optimization
 *
 * 최적화: CPU 코어 기반 동적 워커 수 조정
 * 1. CPU 코어 수 감지
 * 2. 메모리 기반 워커 수 제한
 * 3. 배치 크기 동적 조정
 * 4. 워커당 작업 큐 관리
 *
 * 기대 효과:
 * - CPU 활용율 최적화 (75-85% → 90-95%)
 * - 처리량 15% 증가 (687K → 790K tests/sec)
 * - 메모리 효율 개선 (배치 크기 최적화)
 */

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// ============================================================================
// Object Pools (재사용)
// ============================================================================

class TaskPool {
  constructor(initialSize = 100) {
    this.pool = [];
    this.initialSize = initialSize;
    this.totalAllocations = 0;
    this.totalReuses = 0;

    for (let i = 0; i < initialSize; i++) {
      this.pool.push(this._createTask());
    }
  }

  _createTask() {
    return {
      data: null,
      resolve: null,
      reject: null,
      id: null,
      timestamp: 0
    };
  }

  acquire(data, resolve, reject) {
    let task;
    if (this.pool.length > 0) {
      task = this.pool.pop();
      this.totalReuses++;
    } else {
      task = this._createTask();
      this.totalAllocations++;
    }

    task.data = data;
    task.resolve = resolve;
    task.reject = reject;
    task.id = Math.random();
    task.timestamp = Date.now();

    return task;
  }

  release(task) {
    task.data = null;
    task.resolve = null;
    task.reject = null;
    task.id = null;
    task.timestamp = 0;
    this.pool.push(task);
  }

  getStats() {
    return {
      poolSize: this.pool.length,
      totalAllocations: this.totalAllocations,
      totalReuses: this.totalReuses,
      reuseRate: ((this.totalReuses / (this.totalAllocations + this.totalReuses)) * 100).toFixed(2) + '%'
    };
  }
}

class MessagePool {
  constructor(initialSize = 100) {
    this.pool = [];
    this.initialSize = initialSize;
    this.totalAllocations = 0;
    this.totalReuses = 0;

    for (let i = 0; i < initialSize; i++) {
      this.pool.push(this._createMessage());
    }
  }

  _createMessage() {
    return { type: '', data: null, taskId: null };
  }

  acquire(type, data, taskId) {
    let msg;
    if (this.pool.length > 0) {
      msg = this.pool.pop();
      this.totalReuses++;
    } else {
      msg = this._createMessage();
      this.totalAllocations++;
    }

    msg.type = type;
    msg.data = data;
    msg.taskId = taskId;

    return msg;
  }

  release(msg) {
    msg.type = '';
    msg.data = null;
    msg.taskId = null;
    this.pool.push(msg);
  }

  getStats() {
    return {
      poolSize: this.pool.length,
      totalAllocations: this.totalAllocations,
      totalReuses: this.totalReuses,
      reuseRate: ((this.totalReuses / (this.totalAllocations + this.totalReuses)) * 100).toFixed(2) + '%'
    };
  }
}

// ============================================================================
// Worker Configuration
// ============================================================================

class WorkerConfig {
  constructor() {
    this.cpuCores = os.cpus().length;
    this.totalMemory = os.totalmem();
    this.availableMemory = os.freemem();

    // CPU 기반 워커 수 결정
    this.optimalWorkerCount = this._calculateOptimalWorkers();

    // 메모리 기반 배치 크기 결정
    this.optimalBatchSize = this._calculateOptimalBatchSize();

    // 워커당 큐 크기
    this.queueSizePerWorker = 100;
  }

  _calculateOptimalWorkers() {
    // 권장: CPU 코어 수의 50-75%
    // 이유: I/O 바운드 작업이므로 코어 수보다 적게
    const minWorkers = Math.max(2, Math.floor(this.cpuCores * 0.5));
    const maxWorkers = Math.max(4, Math.floor(this.cpuCores * 0.75));

    return Math.min(maxWorkers, minWorkers);
  }

  _calculateOptimalBatchSize() {
    // 메모리 기반 배치 크기 결정
    // 워커당 할당 메모리: 50MB로 제한
    const memoryPerWorker = 50 * 1024 * 1024; // 50MB
    const totalWorkerMemory = this.optimalWorkerCount * memoryPerWorker;

    // 배치당 메모리 추정: 클론당 ~0.5KB
    const memoryPerClone = 0.5 * 1024;
    const batchSize = Math.floor(memoryPerWorker / memoryPerClone);

    // 범위: 5000 ~ 50000
    return Math.max(5000, Math.min(50000, batchSize));
  }

  getConfig() {
    return {
      cpuCores: this.cpuCores,
      totalMemory: (this.totalMemory / (1024 * 1024 * 1024)).toFixed(2) + ' GB',
      availableMemory: (this.availableMemory / (1024 * 1024 * 1024)).toFixed(2) + ' GB',
      optimalWorkerCount: this.optimalWorkerCount,
      optimalBatchSize: this.optimalBatchSize,
      queueSizePerWorker: this.queueSizePerWorker
    };
  }
}

// ============================================================================
// Dynamic Worker Pool
// ============================================================================

class DynamicWorkerPool {
  constructor(config) {
    this.config = config;
    this.numWorkers = config.optimalWorkerCount;
    this.workers = [];
    this.taskQueue = [];
    this.activeWorkers = 0;

    this.taskPool = new TaskPool(100);
    this.messagePool = new MessagePool(100);

    // 워커당 로컬 큐
    this.workerQueues = new Map();

    // 워커 생성
    for (let i = 0; i < this.numWorkers; i++) {
      const worker = new Worker(new URL('clone-worker-pool.mjs', import.meta.url), {
        env: { WORKER_ID: i }
      });

      worker.on('message', (message) => this._handleWorkerMessage(worker, message));
      worker.on('error', (error) => console.error(`Worker ${i} error:`, error));

      const workerInfo = {
        id: i,
        worker,
        busy: false,
        tasksCompleted: 0,
        currentTask: null,
        localQueue: []
      };

      this.workers.push(workerInfo);
      this.workerQueues.set(i, []);
    }
  }

  async runTask(data) {
    return new Promise((resolve, reject) => {
      const task = this.taskPool.acquire(data, resolve, reject);

      const availableWorker = this.workers.find(w => !w.busy);

      if (availableWorker) {
        this._executeTask(availableWorker, task);
      } else {
        // 큐 크기가 가장 작은 워커에 작업 추가
        const targetWorker = this._findOptimalWorker();
        targetWorker.localQueue.push(task);
      }
    });
  }

  _findOptimalWorker() {
    return this.workers.reduce((min, worker) =>
      worker.localQueue.length < min.localQueue.length ? worker : min
    );
  }

  _executeTask(workerInfo, task) {
    workerInfo.busy = true;
    workerInfo.currentTask = task;

    const message = this.messagePool.acquire('process', task.data, task.id);
    workerInfo.worker.postMessage(message);
  }

  _handleWorkerMessage(worker, message) {
    const workerInfo = this.workers.find(w => w.worker === worker);

    if (message.type === 'done') {
      const { currentTask } = workerInfo;

      workerInfo.busy = false;
      workerInfo.tasksCompleted++;

      currentTask.resolve(message.result);
      this.taskPool.release(currentTask);

      // 로컬 큐 확인
      if (workerInfo.localQueue.length > 0) {
        const nextTask = workerInfo.localQueue.shift();
        this._executeTask(workerInfo, nextTask);
      }
    }
  }

  getStats() {
    return {
      config: this.config.getConfig(),
      workers: this.workers.map(w => ({
        workerId: w.id,
        tasksCompleted: w.tasksCompleted,
        busy: w.busy,
        queueSize: w.localQueue.length
      })),
      globalQueueSize: this.taskQueue.length,
      taskPoolStats: this.taskPool.getStats()
    };
  }

  async terminate() {
    for (const { worker } of this.workers) {
      await worker.terminate();
    }
  }
}

// ============================================================================
// Clone Test Engine with Worker Tuning
// ============================================================================

class CloneTestEngineTuned {
  constructor() {
    this.config = new WorkerConfig();
    this.workerPool = new DynamicWorkerPool(this.config);

    // 동적 설정값
    this.totalClones = 100000000;
    this.batchSize = this.config.optimalBatchSize;
    this.numWorkers = this.config.optimalWorkerCount;

    this.stats = {
      total: 0,
      completed: 0,
      success: 0,
      failed: 0,
      distributionTime: 0,
      processingTime: 0
    };

    this.appMap = {
      proof_ai: 0,
      cwm: 1,
      freelang: 2,
      kim_ai_os: 3
    };
  }

  async runBatchDistributed(appNameStr, totalBatches) {
    const startTime = Date.now();
    const batchesPerWorker = Math.ceil(totalBatches / this.numWorkers);

    console.log(`\n📊 분산 처리 설정 (동적 워커 튜닝):`);
    console.log(`   CPU 코어: ${this.config.cpuCores}`);
    console.log(`   최적 워커 수: ${this.numWorkers}`);
    console.log(`   배치 크기: ${this.batchSize.toLocaleString()}`);
    console.log(`   총 배치: ${totalBatches}`);
    console.log(`   배치/워커: ${batchesPerWorker}\n`);

    console.log('⚙️  워커 태스크 분배:');

    const workerPromises = [];

    for (let workerIdx = 0; workerIdx < this.numWorkers; workerIdx++) {
      const startBatch = workerIdx * batchesPerWorker;
      const endBatch = Math.min(startBatch + batchesPerWorker, totalBatches);
      const batchCount = endBatch - startBatch;

      console.log(`   워커 ${workerIdx}: 배치 ${startBatch}~${endBatch - 1} (${batchCount}개)`);

      const promise = this.workerPool.runTask({
        appName: appNameStr,
        startBatch,
        endBatch,
        batchSize: this.batchSize,
        totalClones: this.totalClones
      });

      workerPromises.push(promise);
    }

    this.stats.distributionTime = Date.now() - startTime;

    console.log(`\n⏳ 워커 실행 중...\n`);

    const processingStart = Date.now();
    const results = await Promise.all(workerPromises);

    this.stats.processingTime = Date.now() - processingStart;

    let totalTests = 0;
    let totalSuccess = 0;

    results.forEach((result, idx) => {
      console.log(`✅ 워커 ${idx} 완료: ${result.tests} 테스트, ${result.success} 성공`);
      totalTests += result.tests;
      totalSuccess += result.success;
    });

    return {
      totalTests,
      totalSuccess,
      totalFailed: totalTests - totalSuccess,
      processingTime: this.stats.processingTime,
      distributionTime: this.stats.distributionTime
    };
  }

  async massTestDistributed(appName, batches = 5) {
    console.log(`\n${'═'.repeat(70)}`);
    console.log(`🚀 Priority 8: 동적 워커 튜닝 테스트`);
    console.log(`${'═'.repeat(70)}`);

    console.log(`\n🔥 ${appName.toUpperCase()} 무차별 폭격 (동적 튜닝)!`);
    console.log(`테스트: ${(batches * this.batchSize).toLocaleString()} 클론`);

    const result = await this.runBatchDistributed(appName, batches);

    const totalTime = result.processingTime + result.distributionTime;
    const successRate = ((result.totalSuccess / result.totalTests) * 100).toFixed(2);
    const tps = Math.floor(result.totalTests / (result.processingTime / 1000));

    return {
      app: appName,
      total_tests: result.totalTests,
      success: result.totalSuccess,
      failed: result.totalFailed,
      duration_ms: totalTime,
      processing_ms: result.processingTime,
      distribution_ms: result.distributionTime,
      tests_per_second: tps,
      success_rate: successRate + '%',
      worker_stats: this.workerPool.getStats()
    };
  }

  async multiAppTestDistributed() {
    const apps = ['proof_ai', 'cwm', 'freelang', 'kim_ai_os'];
    const results = [];

    for (const app of apps) {
      const result = await this.massTestDistributed(app, 3);
      results.push(result);
    }

    console.log(`\n${'═'.repeat(70)}`);
    console.log(`📊 Priority 8 결과 (동적 워커 튜닝)`);
    console.log(`${'═'.repeat(70)}\n`);

    console.log(`🖥️  시스템 설정:`);
    const config = this.config.getConfig();
    console.log(`   CPU 코어: ${config.cpuCores}`);
    console.log(`   전체 메모리: ${config.totalMemory}`);
    console.log(`   사용 가능: ${config.availableMemory}`);
    console.log(`   최적 워커 수: ${config.optimalWorkerCount}`);
    console.log(`   최적 배치 크기: ${config.optimalBatchSize.toLocaleString()}\n`);

    let totalTests = 0;
    let totalSuccess = 0;
    let maxTps = 0;

    results.forEach(r => {
      totalTests += r.total_tests;
      totalSuccess += r.success;
      maxTps = Math.max(maxTps, r.tests_per_second);

      console.log(`📱 ${r.app}`);
      console.log(`   총: ${r.total_tests.toLocaleString()} | 성공: ${r.success} | 실패: ${r.failed}`);
      console.log(`   성공율: ${r.success_rate} | 처리량: ${r.tests_per_second.toLocaleString()} tests/sec`);
      console.log(`   큐 크기: ${r.worker_stats.workers.map(w => w.queueSize).join('/')}\n`);
    });

    const overallSuccess = ((totalSuccess / totalTests) * 100).toFixed(2);
    console.log(`\n📈 전체 통계:`);
    console.log(`   총 테스트: ${totalTests.toLocaleString()}`);
    console.log(`   총 성공: ${totalSuccess.toLocaleString()}`);
    console.log(`   전체 성공율: ${overallSuccess}%`);
    console.log(`   최대 처리량: ${maxTps.toLocaleString()} tests/sec`);
    console.log(`   예상 100M 처리 시간: ${(100000000 / maxTps).toFixed(2)}초\n`);

    return results;
  }
}

// ============================================================================
// Main
// ============================================================================

async function main() {
  const engine = new CloneTestEngineTuned();

  try {
    const results = await engine.multiAppTestDistributed();
    await engine.workerPool.terminate();
    process.exit(0);
  } catch (error) {
    console.error('❌ 에러:', error);
    process.exit(1);
  }
}

main();
