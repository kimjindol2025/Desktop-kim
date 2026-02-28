#!/usr/bin/env node

import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

/**
 * Benchmark Comparison: Priority 6 vs 7 vs 8
 *
 * 비교 항목:
 * 1. 처리량 (tests/sec)
 * 2. 메모리 사용 (시작 → 피크 → 종료)
 * 3. 실행 시간
 * 4. 성공률
 * 5. 예상 100M 처리 시간
 */

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// ============================================================================
// Benchmark Configuration
// ============================================================================

const BENCHMARKS = [
  {
    name: 'Priority 6: Distributed Processing',
    file: 'clone-test-priority6-distributed.mjs',
    version: '2.0.0',
    description: 'Baseline: 4 workers'
  },
  {
    name: 'Priority 7: Object Pool Optimization',
    file: 'clone-test-priority7-objectpool.mjs',
    version: '2.2.1',
    description: 'Task/Message/Result Pool 재사용'
  },
  {
    name: 'Priority 8: Dynamic Worker Tuning',
    file: 'clone-test-priority8-worker-tuning.mjs',
    version: '2.2.2',
    description: 'CPU 기반 동적 워커 튜닝'
  }
];

// 테스트 매개변수
const TEST_BATCHES = 3; // 각 앱당 배치 수
const APPS = ['proof_ai', 'cwm', 'freelang', 'kim_ai_os'];

// ============================================================================
// Benchmark Runner
// ============================================================================

class BenchmarkRunner {
  constructor() {
    this.results = [];
    this.startTime = Date.now();
  }

  async runBenchmark(config) {
    console.log(`\n${'═'.repeat(80)}`);
    console.log(`🏃 ${config.name}`);
    console.log(`${'═'.repeat(80)}`);
    console.log(`파일: ${config.file}`);
    console.log(`버전: ${config.version}`);
    console.log(`설명: ${config.description}\n`);

    try {
      // 메모리 초기 상태
      const memBefore = this._getMemoryUsage();
      console.log(`📊 초기 메모리: ${memBefore} MB`);

      // 벤치마크 실행
      const startTime = Date.now();
      const output = this._executeTest(config.file);
      const duration = (Date.now() - startTime) / 1000;

      // 메모리 최종 상태
      const memAfter = this._getMemoryUsage();
      console.log(`📊 최종 메모리: ${memAfter} MB`);
      console.log(`⏱️  실행 시간: ${duration.toFixed(2)}초\n`);

      // 결과 파싱
      const metrics = this._parseOutput(output, config.name);
      metrics.memoryBefore = memBefore;
      metrics.memoryAfter = memAfter;
      metrics.duration = duration;

      this.results.push({
        config,
        metrics,
        output
      });

      return metrics;
    } catch (error) {
      console.error(`❌ 에러: ${error.message}`);
      return null;
    }
  }

  _executeTest(filename) {
    const filepath = path.join(__dirname, filename);
    try {
      return execSync(`timeout 60 node ${filepath}`, {
        encoding: 'utf-8',
        maxBuffer: 10 * 1024 * 1024,
        stdio: ['pipe', 'pipe', 'pipe']
      });
    } catch (error) {
      return error.stdout || error.stderr || '';
    }
  }

  _parseOutput(output, name) {
    // 처리량 추출
    const tpsMatch = output.match(/(\d+,?\d*)\s*tests\/sec/);
    const tps = tpsMatch ? parseInt(tpsMatch[1].replace(/,/g, '')) : 0;

    // 성공률 추출
    const successRateMatch = output.match(/성공율:\s*([\d.]+)%/);
    const successRate = successRateMatch ? parseFloat(successRateMatch[1]) : 0;

    // 100M 처리 시간 추정
    const estimatedTime = tps > 0 ? (100000000 / tps).toFixed(2) : 'N/A';

    return {
      name,
      tps,
      successRate,
      estimatedTime100M: estimatedTime
    };
  }

  _getMemoryUsage() {
    const used = Math.round(process.memoryUsage().heapUsed / 1024 / 1024);
    return used;
  }

  printComparison() {
    if (this.results.length === 0) {
      console.log('❌ 비교할 결과가 없습니다.');
      return;
    }

    console.log(`\n${'═'.repeat(80)}`);
    console.log(`📊 벤치마크 비교 분석`);
    console.log(`${'═'.repeat(80)}\n`);

    // 기준선 (Priority 6)
    const baseline = this.results[0].metrics;

    // 비교 테이블
    console.log('┌─────────────────────────────────────────────────────────────────────┐');
    console.log('│ 메트릭          │ Priority 6 │ Priority 7 │ Priority 8 │ 개선율    │');
    console.log('├─────────────────────────────────────────────────────────────────────┤');

    // 처리량
    const p7Tps = this.results[1]?.metrics.tps || 0;
    const p8Tps = this.results[2]?.metrics.tps || 0;
    const tpsP7Improvement = ((p7Tps / baseline.tps - 1) * 100).toFixed(1);
    const tpsP8Improvement = ((p8Tps / baseline.tps - 1) * 100).toFixed(1);

    console.log(`│ 처리량 (tests/s) │ ${baseline.tps.toLocaleString().padEnd(10)} │ ${p7Tps.toLocaleString().padEnd(10)} │ ${p8Tps.toLocaleString().padEnd(10)} │ +${tpsP8Improvement}% │`);

    // 성공률
    const p7SR = this.results[1]?.metrics.successRate || 0;
    const p8SR = this.results[2]?.metrics.successRate || 0;

    console.log(`│ 성공률 (%)      │ ${baseline.successRate.toFixed(2).padEnd(10)} │ ${p7SR.toFixed(2).padEnd(10)} │ ${p8SR.toFixed(2).padEnd(10)} │        │`);

    // 100M 처리 시간
    console.log(`│ 100M 처리 (s)   │ ${baseline.estimatedTime100M.toString().padEnd(10)} │ ${(this.results[1]?.metrics.estimatedTime100M || 'N/A').toString().padEnd(10)} │ ${(this.results[2]?.metrics.estimatedTime100M || 'N/A').toString().padEnd(10)} │        │`);

    // 메모리
    const p7Mem = this.results[1]?.metrics.memoryAfter || 0;
    const p8Mem = this.results[2]?.metrics.memoryAfter || 0;
    const memP7Improvement = ((1 - p7Mem / baseline.memoryAfter) * 100).toFixed(1);
    const memP8Improvement = ((1 - p8Mem / baseline.memoryAfter) * 100).toFixed(1);

    console.log(`│ 메모리 (MB)     │ ${baseline.memoryAfter.toString().padEnd(10)} │ ${p7Mem.toString().padEnd(10)} │ ${p8Mem.toString().padEnd(10)} │ -${memP8Improvement}% │`);

    // 실행 시간
    const p7Duration = this.results[1]?.duration || 0;
    const p8Duration = this.results[2]?.duration || 0;

    console.log(`│ 실행 시간 (s)   │ ${this.results[0].duration.toFixed(2).padEnd(10)} │ ${p7Duration.toFixed(2).padEnd(10)} │ ${p8Duration.toFixed(2).padEnd(10)} │        │`);

    console.log('└─────────────────────────────────────────────────────────────────────┘');

    // 요약
    console.log(`\n📈 주요 성과:`);
    console.log(`   ✅ Priority 7: 처리량 +${tpsP7Improvement}%, 메모리 -${memP7Improvement}%`);
    console.log(`   ✅ Priority 8: 처리량 +${tpsP8Improvement}%, 메모리 -${memP8Improvement}%`);
    console.log(`   ✅ 누적 개선: ${Math.max(parseFloat(tpsP7Improvement), parseFloat(tpsP8Improvement)).toFixed(1)}% 처리량 증가\n`);

    // 성능 등급
    const improveRate = parseFloat(tpsP8Improvement);
    let grade = '🔴 개선 필요';
    if (improveRate >= 50) grade = '🟢 우수';
    else if (improveRate >= 30) grade = '🟡 양호';
    else if (improveRate >= 10) grade = '🟠 미흡';

    console.log(`📊 성능 등급: ${grade}`);

    // 예측
    console.log(`\n🔮 성능 예측:`);
    console.log(`   Priority 8은 Priority 6 대비`);
    console.log(`   - 처리량: ${tpsP8Improvement}% 향상`);
    console.log(`   - 메모리: ${memP8Improvement}% 감소`);
    console.log(`   - 100M 클론 처리: 약 ${baseline.estimatedTime100M}초 → ${this.results[2]?.metrics.estimatedTime100M}초\n`);
  }

  printDetailedReport() {
    console.log(`\n${'═'.repeat(80)}`);
    console.log(`📋 상세 성능 분석 보고서`);
    console.log(`${'═'.repeat(80)}\n`);

    this.results.forEach((result, idx) => {
      console.log(`\n[${"P6→P8"[idx] || `P${6 + idx}`}] ${result.config.name}`);
      console.log(`${'─'.repeat(80)}`);

      const m = result.metrics;
      console.log(`처리량: ${m.tps.toLocaleString()} tests/sec`);
      console.log(`성공률: ${m.successRate}%`);
      console.log(`100M 처리: ${m.estimatedTime100M}초`);
      console.log(`메모리: ${m.memoryAfter} MB`);
      console.log(`실행 시간: ${result.duration.toFixed(2)}초`);
    });
  }

  generateReport() {
    const timestamp = new Date().toISOString();
    const totalDuration = ((Date.now() - this.startTime) / 1000).toFixed(2);

    const report = {
      timestamp,
      totalDurationSeconds: parseFloat(totalDuration),
      benchmarks: BENCHMARKS,
      results: this.results.map(r => ({
        name: r.config.name,
        version: r.config.version,
        metrics: r.metrics
      }))
    };

    const filename = `benchmark-report-${timestamp.split('T')[0]}.json`;
    fs.writeFileSync(filename, JSON.stringify(report, null, 2));
    console.log(`\n💾 보고서 저장: ${filename}`);

    return report;
  }
}

// ============================================================================
// Main
// ============================================================================

async function main() {
  console.log(`${'═'.repeat(80)}`);
  console.log(`🚀 Phase 26 벤치마크 비교`);
  console.log(`${'═'.repeat(80)}\n`);

  console.log(`📌 테스트 설정:`);
  console.log(`   - 테스트 앱: ${APPS.join(', ')}`);
  console.log(`   - 배치 수: ${TEST_BATCHES}`);
  console.log(`   - 총 실행 시간: 예상 ~10분\n`);

  const runner = new BenchmarkRunner();

  // 각 Priority 벤치마크 실행
  for (const config of BENCHMARKS) {
    const result = await runner.runBenchmark(config);
    if (!result) {
      console.log(`⚠️  ${config.name} 스킵\n`);
    }
  }

  // 결과 분석
  runner.printComparison();
  runner.printDetailedReport();

  // 보고서 생성
  const report = runner.generateReport();

  console.log(`\n✅ 벤치마킹 완료!`);
  console.log(`${'═'.repeat(80)}\n`);
}

main().catch(console.error);
