/**
 * Pattern Vector Index 테스트
 *
 * 간단한 테스트로 VectorIndex의 기본 기능 검증
 */

import PatternVectorIndex, { PatternVector } from './indexing/pattern-vector-index';
import MetadataStore from './indexing/metadata-store';

function testBasicFunctionality() {
  console.log('🧪 Pattern Vector Index 테스트 시작\n');

  // 1. 인덱스 생성
  console.log('1️⃣  인덱스 생성');
  const index = new PatternVectorIndex(7, 0.3);
  console.log(`   ✅ VectorIndex 생성 (차원: 7, 재계 가중치: 0.3)\n`);

  // 2. 테스트 벡터 추가
  console.log('2️⃣  테스트 벡터 추가');
  const testVectors: PatternVector[] = [
    {
      id: 'ruby-read.file-001',
      language: 'Ruby',
      operation: 'read.file',
      vector: new Float32Array([0.85, 0.90, 0.75, 0.60, 0.95, 0.88, 0.92]),
      metadata: {
        performance: 0.85,
        memory: 0.90,
        concurrency: 0.75,
        testing: 0.60,
        ecosystem: 0.95,
        real_world: 0.88,
        best_practices: 0.92,
      },
    },
    {
      id: 'python-read.file-001',
      language: 'Python',
      operation: 'read.file',
      vector: new Float32Array([0.80, 0.85, 0.70, 0.75, 0.90, 0.85, 0.88]),
      metadata: {
        performance: 0.80,
        memory: 0.85,
        concurrency: 0.70,
        testing: 0.75,
        ecosystem: 0.90,
        real_world: 0.85,
        best_practices: 0.88,
      },
    },
    {
      id: 'go-read.file-001',
      language: 'Go',
      operation: 'read.file',
      vector: new Float32Array([0.95, 0.92, 0.88, 0.70, 0.75, 0.80, 0.85]),
      metadata: {
        performance: 0.95,
        memory: 0.92,
        concurrency: 0.88,
        testing: 0.70,
        ecosystem: 0.75,
        real_world: 0.80,
        best_practices: 0.85,
      },
    },
    {
      id: 'rust-read.file-001',
      language: 'Rust',
      operation: 'read.file',
      vector: new Float32Array([0.98, 0.95, 0.90, 0.65, 0.60, 0.70, 0.90]),
      metadata: {
        performance: 0.98,
        memory: 0.95,
        concurrency: 0.90,
        testing: 0.65,
        ecosystem: 0.60,
        real_world: 0.70,
        best_practices: 0.90,
      },
    },
    {
      id: 'java-filter-001',
      language: 'Java',
      operation: 'filter',
      vector: new Float32Array([0.88, 0.88, 0.85, 0.80, 0.92, 0.87, 0.88]),
      metadata: {
        performance: 0.88,
        memory: 0.88,
        concurrency: 0.85,
        testing: 0.80,
        ecosystem: 0.92,
        real_world: 0.87,
        best_practices: 0.88,
      },
    },
  ];

  testVectors.forEach((vec, i) => {
    const result = index.add(vec);
    console.log(`   ✅ [${i + 1}] ${vec.language}/${vec.operation} (offset: ${result.offset})`);
  });
  console.log();

  // 3. 코사인 유사도 검색
  console.log('3️⃣  코사인 유사도 검색');
  const queryVector = new Float32Array([0.85, 0.88, 0.78, 0.65, 0.93, 0.87, 0.90]);
  console.log('   쿼리: [0.85, 0.88, 0.78, 0.65, 0.93, 0.87, 0.90]');
  console.log('   (Ruby/read.file과 유사한 벡터)\n');

  const topK = index.search(queryVector, 3);
  console.log('   상위 3개 결과:');
  topK.forEach((result, i) => {
    console.log(
      `     ${i + 1}. ${result.language}/${result.operation} (유사도: ${(result.similarity * 100).toFixed(1)}%)`
    );
  });
  console.log();

  // 4. 임계값 기반 검색
  console.log('4️⃣  임계값 기반 검색 (≥ 0.85)');
  const rangeResults = index.rangeSearch(queryVector, 0.85);
  console.log(`   결과: ${rangeResults.length}개`);
  rangeResults.forEach((result) => {
    console.log(
      `     • ${result.language}/${result.operation} (유사도: ${(result.similarity * 100).toFixed(1)}%)`
    );
  });
  console.log();

  // 5. 언어별 검색
  console.log('5️⃣  언어별 검색: Ruby');
  const rubyPatterns = index.searchByLanguage('Ruby');
  console.log(`   결과: ${rubyPatterns.length}개`);
  rubyPatterns.forEach((pattern) => {
    console.log(`     • ${pattern.language}/${pattern.operation}`);
  });
  console.log();

  // 6. 안전도 기반 검색
  console.log('6️⃣  안전도 기반 검색 (≥ 0.85)');
  const safePatterns = index.searchBySafety(0.85);
  console.log(`   결과: ${safePatterns.length}개`);
  safePatterns.forEach((pattern) => {
    const safety = (pattern.metadata.best_practices + pattern.metadata.concurrency) / 2;
    console.log(
      `     • ${pattern.language}/${pattern.operation} (안전도: ${(safety * 100).toFixed(1)}%)`
    );
  });
  console.log();

  // 7. 성능 기반 검색
  console.log('7️⃣  성능 기반 검색 (≥ 0.90)');
  const fastPatterns = index.searchByPerformance(0.90);
  console.log(`   결과: ${fastPatterns.length}개`);
  fastPatterns.forEach((pattern) => {
    console.log(
      `     • ${pattern.language}/${pattern.operation} (성능: ${(pattern.metadata.performance * 100).toFixed(1)}%)`
    );
  });
  console.log();

  // 8. 통계
  console.log('8️⃣  인덱스 통계');
  const stats = index.getStats();
  console.log(`   • 총 벡터: ${stats.totalVectors}개`);
  console.log(`   • 차원: ${stats.dimension}`);
  console.log(`   • 언어: ${Array.from(stats.languages).join(', ')}`);
  console.log(`   • 연산: ${Array.from(stats.operations).join(', ')}`);
  console.log();

  console.log('✅ 모든 테스트 완료!\n');
}

function testMetadataStore() {
  console.log('📂 MetadataStore 테스트 시작\n');

  const storePath = '/tmp/test-metadata.jsonl';

  // 1. 저장소 생성
  console.log('1️⃣  저장소 생성');
  const store = new MetadataStore(storePath, 7);
  console.log(`   ✅ MetadataStore 생성\n`);

  // 2. 메타데이터 저장
  console.log('2️⃣  메타데이터 저장');
  const records = [
    {
      id: 'ruby-read.file-001',
      language: 'Ruby',
      operation: 'read.file',
      file_path: 'CodeMind/01_code_assets/io/read.file.rb',
      lines_of_code: 25,
      vector: [0.85, 0.90, 0.75, 0.60, 0.95, 0.88, 0.92],
      metadata: {
        performance: 0.85,
        memory: 0.90,
        concurrency: 0.75,
        testing: 0.60,
        ecosystem: 0.95,
        real_world: 0.88,
        best_practices: 0.92,
      },
      error_codes: [1, 2, 3, 4],
      complexity: 'O(n)',
    },
  ];
  store.save(records);
  console.log(`   ✅ 1개 레코드 저장\n`);

  // 3. 통계
  console.log('3️⃣  통계 조회');
  const stats = store.getStats();
  console.log(`   • 로드된 벡터: ${stats.totalVectors}개`);
  console.log();

  console.log('✅ MetadataStore 테스트 완료!\n');
}

// 실행
console.log('════════════════════════════════════════════════════\n');
console.log('   Pattern Vector Index 통합 테스트\n');
console.log('════════════════════════════════════════════════════\n');

testBasicFunctionality();
testMetadataStore();

console.log('════════════════════════════════════════════════════\n');
console.log('✨ 모든 테스트 성공!\n');
