#!/usr/bin/env node

import { Worker } from 'worker_threads';
import http from 'http';
import path from 'path';
import { fileURLToPath } from 'url';

/**
 * Clone Test Engine - Priority 7: Object Pool Optimization
 *
 * 최적화: 메모리 할당 최소화
 * 1. Task Object Pool - 재사용 가능한 Task 객체 풀
 * 2. Message Object Pool - postMessage 데이터 재사용
 * 3. Result Object Pool - 결과 객체 재사용
 *
 * 기대 효과:
 * - 메모리 할당 20% 감소
 * - GC 압력 50% 감소
 * - 처리량 25% 증가 (550K → 687K tests/sec)
 */

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// ============================================================================
// Object Pools
// ============================================================================

/**
 * Task Object Pool - Task 객체 재사용
 */
class TaskPool {
  constructor(initialSize = 100) {
    this.pool = [];
    this.initialSize = initialSize;
    this.totalAllocations = 0;
    this.totalReuses = 0;

    // 초기 객체 생성
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

/**
 * Message Object Pool - postMessage 데이터 재사용
 */
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
    return {
      type: '',
      data: null,
      taskId: null
    };
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

/**
 * Result Object Pool - 결과 객체 재사용
 */
class ResultPool {
  constructor(initialSize = 50) {
    this.pool = [];
    this.initialSize = initialSize;
    this.totalAllocations = 0;
    this.totalReuses = 0;

    for (let i = 0; i < initialSize; i++) {
      this.pool.push(this._createResult());
    }
  }

  _createResult() {
    return {
      tests: 0,
      success: 0,
      failed: 0,
      duration: 0,
      workerId: null
    };
  }

  acquire(tests, success, duration, workerId) {
    let result;
    if (this.pool.length > 0) {
      result = this.pool.pop();
      this.totalReuses++;
    } else {
      result = this._createResult();
      this.totalAllocations++;
    }

    result.tests = tests;
    result.success = success;
    result.failed = tests - success;
    result.duration = duration;
    result.workerId = workerId;

    return result;
  }

  release(result) {
    result.tests = 0;
    result.success = 0;
    result.failed = 0;
    result.duration = 0;
    result.workerId = null;
    this.pool.push(result);
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
// Worker Pool with Object Pools
// ============================================================================

class WorkerPoolOptimized {
  constructor(numWorkers = 4, objectPoolSize = 100) {
    this.numWorkers = numWorkers;
    this.workers = [];
    this.taskQueue = [];
    this.activeWorkers = 0;

    // Object Pools
    this.taskPool = new TaskPool(objectPoolSize);
    this.messagePool = new MessagePool(objectPoolSize);
    this.resultPool = new ResultPool(objectPoolSize / 2);

    // 워커 생성
    for (let i = 0; i < numWorkers; i++) {
      const worker = new Worker(new URL('clone-worker-pool.mjs', import.meta.url), {
        env: { WORKER_ID: i }
      });

      worker.on('message', (message) => this._handleWorkerMessage(worker, message));
      worker.on('error', (error) => console.error(`Worker ${i} error:`, error));
      worker.on('exit', (code) => console.log(`Worker ${i} exited with code ${code}`));

      this.workers.push({
        id: i,
        worker,
        busy: false,
        tasksCompleted: 0,
        currentTask: null
      });
    }
  }

  async runTask(data) {
    return new Promise((resolve, reject) => {
      const task = this.taskPool.acquire(data, resolve, reject);

      // 사용 가능한 워커 찾기
      const availableWorker = this.workers.find(w => !w.busy);

      if (availableWorker) {
        this._executeTask(availableWorker, task);
      } else {
        // 대기열에 추가
        this.taskQueue.push(task);
      }
    });
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
      const result = this.resultPool.acquire(
        message.result.tests,
        message.result.success,
        message.result.duration,
        workerInfo.id
      );

      workerInfo.busy = false;
      workerInfo.tasksCompleted++;

      // 원본 task 결과 전달 후 pool에 반환
      currentTask.resolve(message.result);
      this.taskPool.release(currentTask);
      this.resultPool.release(result);

      // 대기 중인 작업 처리
      if (this.taskQueue.length > 0) {
        const nextTask = this.taskQueue.shift();
        this._executeTask(workerInfo, nextTask);
      }
    }
  }

  getStats() {
    return {
      workers: this.workers.map(w => ({
        workerId: w.id,
        tasksCompleted: w.tasksCompleted,
        busy: w.busy
      })),
      pools: {
        taskPool: this.taskPool.getStats(),
        messagePool: this.messagePool.getStats(),
        resultPool: this.resultPool.getStats()
      }
    };
  }

  async terminate() {
    for (const { worker } of this.workers) {
      await worker.terminate();
    }
  }
}

// ============================================================================
// Clone Test Engine with Object Pool Optimization
// ============================================================================

class CloneTestEngineOptimized {
  constructor(totalClones = 100000000, objectPoolSize = 100) {
    this.totalClones = totalClones;
    this.batchSize = 10000;
    this.numWorkers = 4;
    this.workerPool = new WorkerPoolOptimized(this.numWorkers, objectPoolSize);
    this.objectPoolSize = objectPoolSize;

    this.stats = {
      total: 0,
      completed: 0,
      success: 0,
      failed: 0,
      distributionTime: 0,
      processingTime: 0,
      memoryBefore: 0,
      memoryAfter: 0
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

    console.log(`\n📊 분산 처리 설정 (Object Pool 최적화):`);
    console.log(`   총 배치: ${totalBatches}`);
    console.log(`   워커 수: ${this.numWorkers}`);
    console.log(`   배치/워커: ${batchesPerWorker}`);
    console.log(`   Object Pool 초기 크기: ${this.objectPoolSize}\n`);

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

    // 결과 병합
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
    console.log(`🚀 Priority 7: Object Pool 최적화 테스트`);
    console.log(`${'═'.repeat(70)}`);

    console.log(`\n🔥 ${appName.toUpperCase()} 무차별 폭격 (Object Pool)!`);
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
      pool_stats: this.workerPool.getStats()
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
    console.log(`📊 Priority 7 결과 (Object Pool 최적화)`);
    console.log(`${'═'.repeat(70)}\n`);

    // Object Pool 통계
    const firstResult = results[0];
    if (firstResult.pool_stats.pools) {
      console.log(`\n💾 Object Pool 재사용률:`);
      console.log(`   Task Pool: ${firstResult.pool_stats.pools.taskPool.reuseRate}`);
      console.log(`   Message Pool: ${firstResult.pool_stats.pools.messagePool.reuseRate}`);
      console.log(`   Result Pool: ${firstResult.pool_stats.pools.resultPool.reuseRate}\n`);
    }

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
      console.log(`   총 시간: ${(r.duration_ms / 1000).toFixed(3)}초\n`);
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

  async httpServer(port = 19936) {
    const server = http.createServer(async (req, res) => {
      if (req.url === '/metrics') {
        const stats = this.workerPool.getStats();
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(stats, null, 2));
      } else if (req.url === '/test') {
        const result = await this.massTestDistributed('proof_ai', 1);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(result, null, 2));
      } else {
        res.writeHead(200, { 'Content-Type': 'text/plain' });
        res.end('Clone Test Engine - Priority 7 (Object Pool)\nEndpoints: /test, /metrics');
      }
    });

    server.listen(port, () => {
      console.log(`🌐 HTTP 서버 시작: http://localhost:${port}`);
    });
  }
}

// ============================================================================
// Main
// ============================================================================

async function main() {
  const engine = new CloneTestEngineOptimized(100000000, 100);

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
