/**
 * Multi-Heuristic Scoring
 *
 * Test-Language-Search 알고리즘을 패턴에 적용
 * 5개 요소의 가중 조합으로 최종 점수 계산
 *
 * 가중치 배분:
 *   • 태그 매칭: 30%
 *   • 키워드 매칭: 25%
 *   • 시맨틱 유사도: 20%
 *   • 성능 지표: 15%
 *   • 복잡도 점수: 10%
 */

export interface HeuristicScores {
  tagMatching: number;           // 0.0-1.0 (30%)
  keywordMatching: number;       // 0.0-1.0 (25%)
  semanticSimilarity: number;    // 0.0-1.0 (20%)
  performanceScore: number;      // 0.0-1.0 (15%)
  complexityScore: number;       // 0.0-1.0 (10%)
}

export interface FinalScoreResult extends HeuristicScores {
  finalScore: number;            // 0.0-1.0 (모든 가중치 적용)
  breakdown: {
    tagComponent: number;        // 30% 적용된 값
    keywordComponent: number;    // 25% 적용된 값
    semanticComponent: number;   // 20% 적용된 값
    performanceComponent: number;// 15% 적용된 값
    complexityComponent: number; // 10% 적용된 값
  };
}

export class MultiHeuristicScorer {
  private readonly WEIGHTS = {
    tag: 0.30,
    keyword: 0.25,
    semantic: 0.20,
    performance: 0.15,
    complexity: 0.10,
  };

  /**
   * 태그 매칭 점수 계산
   *
   * 패턴의 태그(언어, 연산)와 쿼리 태그의 일치도
   */
  public calculateTagMatching(
    queryTags: string[],
    patternTags: string[]
  ): number {
    if (queryTags.length === 0 || patternTags.length === 0) {
      return 0;
    }

    const querySet = new Set(queryTags.map(t => t.toLowerCase()));
    const patternSet = new Set(patternTags.map(t => t.toLowerCase()));

    // Jaccard 유사도
    const intersection = new Set(
      [...querySet].filter(x => patternSet.has(x))
    );
    const union = new Set([...querySet, ...patternSet]);

    const score = union.size > 0 ? intersection.size / union.size : 0;
    return Math.max(0, Math.min(1, score));
  }

  /**
   * 키워드 매칭 점수 계산
   *
   * 문서의 키워드와 쿼리 키워드의 일치도
   */
  public calculateKeywordMatching(
    queryKeywords: string[],
    documentKeywords: string[]
  ): number {
    if (queryKeywords.length === 0 || documentKeywords.length === 0) {
      return 0;
    }

    const queryLower = queryKeywords.map(k => k.toLowerCase());
    const docLower = documentKeywords.map(k => k.toLowerCase());

    let matches = 0;
    for (const keyword of queryLower) {
      if (docLower.some(dk => dk.includes(keyword) || keyword.includes(dk))) {
        matches++;
      }
    }

    // TF-based 점수
    const score = matches / queryKeywords.length;
    return Math.max(0, Math.min(1, score));
  }

  /**
   * 시맨틱 유사도
   *
   * 벡터 기반 코사인 유사도 (VectorIndex에서 받음)
   */
  public calculateSemanticSimilarity(
    cosineSimilarity: number
  ): number {
    // 코사인 유사도는 이미 0.0-1.0 범위
    return Math.max(0, Math.min(1, cosineSimilarity));
  }

  /**
   * 성능 점수
   *
   * 실행 시간, 메모리 사용량, 처리량 기반
   */
  public calculatePerformanceScore(
    performanceMetric: number,
    memoryMetric: number,
    concurrencyMetric: number
  ): number {
    // 성능 = 40% 실행시간 + 35% 메모리 + 25% 동시성
    const score =
      performanceMetric * 0.40 +
      memoryMetric * 0.35 +
      concurrencyMetric * 0.25;

    return Math.max(0, Math.min(1, score));
  }

  /**
   * 복잡도 점수
   *
   * 학습 곡선, LOC, 추상화 수준 기반
   * 낮은 복잡도 = 높은 점수
   */
  public calculateComplexityScore(
    linesOfCode: number,
    abstractionLevel: number
  ): number {
    // LOC 정규화 (100줄 기준)
    const locScore = Math.max(0, 1 - (linesOfCode / 100) * 0.5);

    // 최종 복잡도 점수 = 60% LOC + 40% 추상화
    const score = locScore * 0.60 + abstractionLevel * 0.40;

    return Math.max(0, Math.min(1, score));
  }

  /**
   * 모든 휴리스틱 계산
   */
  public calculateAllHeuristics(params: {
    queryTags: string[];
    patternTags: string[];
    queryKeywords: string[];
    documentKeywords: string[];
    cosineSimilarity: number;
    performanceMetric: number;
    memoryMetric: number;
    concurrencyMetric: number;
    linesOfCode: number;
    abstractionLevel: number;
  }): HeuristicScores {
    return {
      tagMatching: this.calculateTagMatching(
        params.queryTags,
        params.patternTags
      ),
      keywordMatching: this.calculateKeywordMatching(
        params.queryKeywords,
        params.documentKeywords
      ),
      semanticSimilarity: this.calculateSemanticSimilarity(
        params.cosineSimilarity
      ),
      performanceScore: this.calculatePerformanceScore(
        params.performanceMetric,
        params.memoryMetric,
        params.concurrencyMetric
      ),
      complexityScore: this.calculateComplexityScore(
        params.linesOfCode,
        params.abstractionLevel
      ),
    };
  }

  /**
   * 최종 점수 계산 (모든 가중치 적용)
   */
  public calculateFinalScore(scores: HeuristicScores): FinalScoreResult {
    const breakdown = {
      tagComponent: scores.tagMatching * this.WEIGHTS.tag,
      keywordComponent: scores.keywordMatching * this.WEIGHTS.keyword,
      semanticComponent: scores.semanticSimilarity * this.WEIGHTS.semantic,
      performanceComponent: scores.performanceScore * this.WEIGHTS.performance,
      complexityComponent: scores.complexityScore * this.WEIGHTS.complexity,
    };

    const finalScore =
      breakdown.tagComponent +
      breakdown.keywordComponent +
      breakdown.semanticComponent +
      breakdown.performanceComponent +
      breakdown.complexityComponent;

    return {
      ...scores,
      finalScore: Math.max(0, Math.min(1, finalScore)),
      breakdown,
    };
  }

  /**
   * 가중치 정보 반환
   */
  public getWeights() {
    return { ...this.WEIGHTS };
  }

  /**
   * 점수 세부 사항 출력 (디버깅용)
   */
  public explainScore(result: FinalScoreResult): string {
    const lines = [
      `총점: ${(result.finalScore * 100).toFixed(1)}%`,
      `├─ 태그 매칭: ${(result.tagMatching * 100).toFixed(1)}% × 30% = ${(result.breakdown.tagComponent * 100).toFixed(1)}%`,
      `├─ 키워드: ${(result.keywordMatching * 100).toFixed(1)}% × 25% = ${(result.breakdown.keywordComponent * 100).toFixed(1)}%`,
      `├─ 시맨틱: ${(result.semanticSimilarity * 100).toFixed(1)}% × 20% = ${(result.breakdown.semanticComponent * 100).toFixed(1)}%`,
      `├─ 성능: ${(result.performanceScore * 100).toFixed(1)}% × 15% = ${(result.breakdown.performanceComponent * 100).toFixed(1)}%`,
      `└─ 복잡도: ${(result.complexityScore * 100).toFixed(1)}% × 10% = ${(result.breakdown.complexityComponent * 100).toFixed(1)}%`,
    ];
    return lines.join('\n');
  }
}

export default MultiHeuristicScorer;
