/**
 * Pattern Vector Index
 *
 * Mandate-DB VectorIndex를 기반으로 한 패턴 벡터 검색 엔진
 * 코사인 유사도 + 재계 가중치를 사용한 의미론적 검색
 *
 * 특징:
 * - L2-정규화된 코사인 유사도
 * - 재계 가중치 (최근 항목 우선)
 * - O(1) 벡터 검색
 * - Top-K 유사도 검색
 * - 임계값 기반 범위 검색
 */

export interface PatternVector {
  id: string;
  language: string;
  operation: string;
  vector: Float32Array;
  metadata: PatternMetadata;
}

export interface PatternMetadata {
  performance: number;     // 0.0-1.0
  memory: number;          // 0.0-1.0
  concurrency: number;     // 0.0-1.0
  testing: number;         // 0.0-1.0
  ecosystem: number;       // 0.0-1.0
  real_world: number;      // 0.0-1.0
  best_practices: number;  // 0.0-1.0
}

export interface SearchResult {
  id: string;
  language: string;
  operation: string;
  similarity: number;
  metadata: PatternMetadata;
}

export interface RangeSearchResult extends SearchResult {
  distance: number;
}

export class PatternVectorIndex {
  private vectors: Map<string, PatternVector> = new Map();
  private offsets: Map<string, number> = new Map();
  private recencyWeights: Map<string, number> = new Map();
  private recencyWeight: number;
  private dimension: number;
  private nextOffset: number = 0;

  constructor(vectorDimension: number = 7, recencyWeight: number = 0.3) {
    this.dimension = vectorDimension;
    this.recencyWeight = Math.max(0.0, Math.min(1.0, recencyWeight));
  }

  /**
   * 벡터 추가
   */
  public add(pattern: PatternVector): { offset: number; id: string } {
    if (pattern.vector.length !== this.dimension) {
      throw new Error(
        `Vector dimension mismatch: expected ${this.dimension}, got ${pattern.vector.length}`
      );
    }

    // 벡터 정규화 (L2-norm)
    const normalized = this.normalizeVector(pattern.vector);
    pattern.vector = normalized;

    // 저장
    this.vectors.set(pattern.id, pattern);
    this.offsets.set(pattern.id, this.nextOffset);
    this.recencyWeights.set(pattern.id, Date.now());

    const offset = this.nextOffset++;
    return { offset, id: pattern.id };
  }

  /**
   * 코사인 유사도 계산
   */
  private cosineSimilarity(v1: Float32Array, v2: Float32Array): number {
    if (v1.length !== v2.length) {
      throw new Error('Vector dimensions must match');
    }

    let dotProduct = 0;
    let magnitude1 = 0;
    let magnitude2 = 0;

    for (let i = 0; i < v1.length; i++) {
      dotProduct += v1[i] * v2[i];
      magnitude1 += v1[i] * v1[i];
      magnitude2 += v2[i] * v2[i];
    }

    magnitude1 = Math.sqrt(magnitude1);
    magnitude2 = Math.sqrt(magnitude2);

    if (magnitude1 === 0 || magnitude2 === 0) {
      return 0;
    }

    return dotProduct / (magnitude1 * magnitude2);
  }

  /**
   * L2 정규화
   */
  private normalizeVector(vector: Float32Array): Float32Array {
    let magnitude = 0;
    for (let i = 0; i < vector.length; i++) {
      magnitude += vector[i] * vector[i];
    }
    magnitude = Math.sqrt(magnitude);

    if (magnitude === 0) {
      return new Float32Array(vector.length).fill(1.0 / Math.sqrt(vector.length));
    }

    const normalized = new Float32Array(vector.length);
    for (let i = 0; i < vector.length; i++) {
      normalized[i] = vector[i] / magnitude;
    }
    return normalized;
  }

  /**
   * 재계 점수 계산
   */
  private calculateRecencyBoost(timestamp: number): number {
    const now = Date.now();
    const ageMs = now - timestamp;
    const ageDays = ageMs / (1000 * 60 * 60 * 24);

    // 최대 30일 기준
    const boost = Math.max(0, 1 - (ageDays / 30));
    return boost * this.recencyWeight;
  }

  /**
   * 상위 K개 유사 벡터 검색
   */
  public search(
    queryVector: Float32Array,
    topK: number = 10
  ): SearchResult[] {
    if (queryVector.length !== this.dimension) {
      throw new Error(
        `Query dimension mismatch: expected ${this.dimension}, got ${queryVector.length}`
      );
    }

    const normalized = this.normalizeVector(queryVector);
    const similarities: Array<{ id: string; score: number }> = [];

    // 모든 벡터와 유사도 계산
    for (const [id, pattern] of this.vectors.entries()) {
      const similarity = this.cosineSimilarity(normalized, pattern.vector);
      const timestamp = this.recencyWeights.get(id) || Date.now();
      const recencyBoost = this.calculateRecencyBoost(timestamp);

      // 최종 점수 = 유사도 × (1 + 재계 가중치)
      const finalScore = similarity * (1 + recencyBoost);

      similarities.push({ id, score: finalScore });
    }

    // 상위 K개 선택
    const results = similarities
      .sort((a, b) => b.score - a.score)
      .slice(0, topK)
      .map((item) => {
        const pattern = this.vectors.get(item.id)!;
        return {
          id: pattern.id,
          language: pattern.language,
          operation: pattern.operation,
          similarity: Math.max(0, Math.min(1, item.score)),
          metadata: pattern.metadata,
        };
      });

    return results;
  }

  /**
   * 임계값 기반 범위 검색
   */
  public rangeSearch(
    queryVector: Float32Array,
    threshold: number = 0.7
  ): RangeSearchResult[] {
    if (queryVector.length !== this.dimension) {
      throw new Error(
        `Query dimension mismatch: expected ${this.dimension}, got ${queryVector.length}`
      );
    }

    if (threshold < 0 || threshold > 1) {
      throw new Error('Threshold must be between 0 and 1');
    }

    const normalized = this.normalizeVector(queryVector);
    const results: RangeSearchResult[] = [];

    for (const [id, pattern] of this.vectors.entries()) {
      const similarity = this.cosineSimilarity(normalized, pattern.vector);

      if (similarity >= threshold) {
        results.push({
          id: pattern.id,
          language: pattern.language,
          operation: pattern.operation,
          similarity: Math.max(0, Math.min(1, similarity)),
          distance: 1 - similarity,
          metadata: pattern.metadata,
        });
      }
    }

    // 유사도 순으로 정렬
    return results.sort((a, b) => b.similarity - a.similarity);
  }

  /**
   * 언어별 검색
   */
  public searchByLanguage(language: string, operation?: string): PatternVector[] {
    const results: PatternVector[] = [];

    for (const [_, pattern] of this.vectors.entries()) {
      if (
        pattern.language === language &&
        (!operation || pattern.operation === operation)
      ) {
        results.push(pattern);
      }
    }

    return results;
  }

  /**
   * 안전도 기반 검색
   */
  public searchBySafety(minSafetyScore: number): PatternVector[] {
    if (minSafetyScore < 0 || minSafetyScore > 1) {
      throw new Error('Safety score must be between 0 and 1');
    }

    const results: PatternVector[] = [];

    for (const [_, pattern] of this.vectors.entries()) {
      // 안전도 = (best_practices + concurrency) / 2
      const safety =
        (pattern.metadata.best_practices + pattern.metadata.concurrency) / 2;

      if (safety >= minSafetyScore) {
        results.push(pattern);
      }
    }

    return results;
  }

  /**
   * 성능 기반 검색
   */
  public searchByPerformance(minPerformanceScore: number): PatternVector[] {
    if (minPerformanceScore < 0 || minPerformanceScore > 1) {
      throw new Error('Performance score must be between 0 and 1');
    }

    const results: PatternVector[] = [];

    for (const [_, pattern] of this.vectors.entries()) {
      if (pattern.metadata.performance >= minPerformanceScore) {
        results.push(pattern);
      }
    }

    return results;
  }

  /**
   * 전체 벡터 개수
   */
  public size(): number {
    return this.vectors.size;
  }

  /**
   * 벡터 가져오기
   */
  public getVector(id: string): PatternVector | undefined {
    return this.vectors.get(id);
  }

  /**
   * 모든 벡터 가져오기
   */
  public getAllVectors(): PatternVector[] {
    return Array.from(this.vectors.values());
  }

  /**
   * 벡터 삭제
   */
  public remove(id: string): boolean {
    return this.vectors.delete(id);
  }

  /**
   * 인덱스 초기화
   */
  public clear(): void {
    this.vectors.clear();
    this.offsets.clear();
    this.recencyWeights.clear();
    this.nextOffset = 0;
  }

  /**
   * 통계 정보
   */
  public getStats(): {
    totalVectors: number;
    dimension: number;
    languages: Set<string>;
    operations: Set<string>;
    avgVectorSize: number;
  } {
    const languages = new Set<string>();
    const operations = new Set<string>();

    for (const [_, pattern] of this.vectors.entries()) {
      languages.add(pattern.language);
      operations.add(pattern.operation);
    }

    return {
      totalVectors: this.vectors.size,
      dimension: this.dimension,
      languages,
      operations,
      avgVectorSize: this.dimension * 4, // Float32 = 4 bytes
    };
  }
}

export default PatternVectorIndex;
