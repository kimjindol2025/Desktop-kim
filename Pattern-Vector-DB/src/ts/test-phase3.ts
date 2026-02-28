/**
 * Phase 3 통합 테스트
 *
 * 다중 휴리스틱 스코어링 + AI Verdict 생성
 */

import MultiHeuristicScorer from './scoring/multi-heuristic';
import SafetyAnalyzer from './scoring/safety-analyzer';
import VerdictGenerator from './scoring/verdict-generator';

function testMultiHeuristic() {
  console.log('🧪 다중 휴리스틱 스코어링 테스트\n');

  const scorer = new MultiHeuristicScorer();

  // 테스트 데이터
  const testCase = {
    queryTags: ['Ruby', 'read.file'],
    patternTags: ['Ruby', 'read.file'],
    queryKeywords: ['memory', 'efficient', 'streaming'],
    documentKeywords: ['streaming', 'chunk', 'io', 'memory', 'efficient'],
    cosineSimilarity: 0.87,
    performanceMetric: 0.85,
    memoryMetric: 0.90,
    concurrencyMetric: 0.75,
    linesOfCode: 25,
    abstractionLevel: 0.80,
  };

  console.log('1️⃣  개별 휴리스틱 계산');
  const heuristics = scorer.calculateAllHeuristics(testCase);
  console.log(`   • 태그 매칭: ${(heuristics.tagMatching * 100).toFixed(1)}%`);
  console.log(`   • 키워드 매칭: ${(heuristics.keywordMatching * 100).toFixed(1)}%`);
  console.log(`   • 시맨틱 유사도: ${(heuristics.semanticSimilarity * 100).toFixed(1)}%`);
  console.log(`   • 성능 점수: ${(heuristics.performanceScore * 100).toFixed(1)}%`);
  console.log(`   • 복잡도 점수: ${(heuristics.complexityScore * 100).toFixed(1)}%`);
  console.log();

  console.log('2️⃣  최종 점수 계산 (가중치 적용)');
  const finalScore = scorer.calculateFinalScore(heuristics);
  console.log(scorer.explainScore(finalScore));
  console.log();
}

function testSafetyAnalyzer() {
  console.log('🔒 안전도 분석 테스트\n');

  const analyzer = new SafetyAnalyzer();

  // Ruby/read.file 패턴 분석
  const safetyAnalysis = analyzer.analyzeSafety({
    language: 'Ruby',
    hasTypeAnnotations: false,
    hasCompileTimeChecks: false,
    hasGarbageCollection: true,
    hasBoundsChecking: true,
    hasNullSafety: false,
    hasChannels: false,
    hasActors: false,
    hasImmutability: false,
    hasExceptionHandling: true,
    hasResultType: false,
    hasValidation: true,
    errorCodeCount: 4,
    hasInputValidation: true,
    hasEncryption: false,
    hasSQLInjectionProtection: false,
    hasXSSProtection: false,
  });

  console.log('1️⃣  안전도 분석 결과:');
  console.log(analyzer.generateSafetyReport(safetyAnalysis));
  console.log();

  // Go 언어 비교
  console.log('2️⃣  Go 언어 비교:');
  const goSafety = analyzer.analyzeSafety({
    language: 'Go',
    hasTypeAnnotations: true,
    hasCompileTimeChecks: true,
    hasGarbageCollection: true,
    hasBoundsChecking: true,
    hasNullSafety: false,  // Go 1.20 이전
    hasChannels: true,
    hasActors: false,
    hasImmutability: false,
    hasExceptionHandling: false,
    hasResultType: true,
    hasValidation: true,
    errorCodeCount: 5,
    hasInputValidation: true,
    hasEncryption: false,
    hasSQLInjectionProtection: false,
    hasXSSProtection: false,
  });

  console.log(analyzer.generateSafetyReport(goSafety));
  console.log();
}

function testVerdictGenerator() {
  console.log('⚖️  AI Verdict 생성 테스트\n');

  const generator = new VerdictGenerator();
  const scorer = new MultiHeuristicScorer();
  const analyzer = new SafetyAnalyzer();

  // Ruby/read.file 종합 판정
  console.log('1️⃣  Ruby/read.file 종합 판정:');
  console.log();

  // 점수 계산
  const heuristics = scorer.calculateAllHeuristics({
    queryTags: ['Ruby', 'read.file'],
    patternTags: ['Ruby', 'read.file'],
    queryKeywords: ['memory', 'efficient', 'streaming'],
    documentKeywords: ['streaming', 'chunk', 'io', 'memory', 'efficient'],
    cosineSimilarity: 0.87,
    performanceMetric: 0.85,
    memoryMetric: 0.90,
    concurrencyMetric: 0.75,
    linesOfCode: 25,
    abstractionLevel: 0.80,
  });

  const finalScore = scorer.calculateFinalScore(heuristics);

  // 안전도 분석
  const safetyAnalysis = analyzer.analyzeSafety({
    language: 'Ruby',
    hasTypeAnnotations: false,
    hasCompileTimeChecks: false,
    hasGarbageCollection: true,
    hasBoundsChecking: true,
    hasNullSafety: false,
    hasChannels: false,
    hasActors: false,
    hasImmutability: false,
    hasExceptionHandling: true,
    hasResultType: false,
    hasValidation: true,
    errorCodeCount: 4,
    hasInputValidation: true,
    hasEncryption: false,
    hasSQLInjectionProtection: false,
    hasXSSProtection: false,
  });

  // Verdict 생성
  const verdict = generator.generateVerdict({
    language: 'Ruby',
    operation: 'read.file',
    heuristicScore: finalScore,
    safetyAnalysis,
    lines_of_code: 25,
  });

  console.log(generator.formatVerdictReport(verdict));
  console.log();

  // Go/read.file과 비교
  console.log('2️⃣  Go/read.file 종합 판정 (성능 우수):');
  console.log();

  const goHeuristics = scorer.calculateAllHeuristics({
    queryTags: ['Go', 'read.file'],
    patternTags: ['Go', 'read.file'],
    queryKeywords: ['memory', 'efficient', 'streaming'],
    documentKeywords: ['streaming', 'goroutine', 'io', 'buffered'],
    cosineSimilarity: 0.92,
    performanceMetric: 0.95,
    memoryMetric: 0.92,
    concurrencyMetric: 0.88,
    linesOfCode: 30,
    abstractionLevel: 0.75,
  });

  const goFinalScore = scorer.calculateFinalScore(goHeuristics);

  const goSafetyAnalysis = analyzer.analyzeSafety({
    language: 'Go',
    hasTypeAnnotations: true,
    hasCompileTimeChecks: true,
    hasGarbageCollection: true,
    hasBoundsChecking: true,
    hasNullSafety: false,
    hasChannels: true,
    hasActors: false,
    hasImmutability: false,
    hasExceptionHandling: false,
    hasResultType: true,
    hasValidation: true,
    errorCodeCount: 5,
    hasInputValidation: true,
    hasEncryption: false,
    hasSQLInjectionProtection: false,
    hasXSSProtection: false,
  });

  const goVerdict = generator.generateVerdict({
    language: 'Go',
    operation: 'read.file',
    heuristicScore: goFinalScore,
    safetyAnalysis: goSafetyAnalysis,
    lines_of_code: 30,
  });

  console.log(generator.formatVerdictReport(goVerdict));
  console.log();
}

// 실행
console.log('\n');
console.log('════════════════════════════════════════════════════\n');
console.log('   Phase 3: 다중 휴리스틱 & AI Verdict 통합 테스트\n');
console.log('════════════════════════════════════════════════════\n');

testMultiHeuristic();
testSafetyAnalyzer();
testVerdictGenerator();

console.log('════════════════════════════════════════════════════\n');
console.log('✨ Phase 3 테스트 완료!\n');
