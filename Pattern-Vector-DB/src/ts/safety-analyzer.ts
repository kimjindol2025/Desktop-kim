/**
 * Safety Analyzer
 *
 * 패턴의 안전도를 다각도에서 분석
 *
 * 평가 항목:
 *   1. 타입 안전성 (Type Safety)
 *   2. 메모리 안전성 (Memory Safety)
 *   3. 동시성 안전성 (Concurrency Safety)
 *   4. 에러 처리 (Error Handling)
 *   5. 보안 (Security)
 */

export interface SafetyAnalysis {
  typeSafety: number;          // 0.0-1.0
  memorySafety: number;        // 0.0-1.0
  concurrencySafety: number;   // 0.0-1.0
  errorHandling: number;       // 0.0-1.0
  security: number;            // 0.0-1.0
  overallSafety: number;       // 0.0-1.0 (평균)
  verdict: 'safe' | 'caution' | 'risky';
  recommendations: string[];
}

export class SafetyAnalyzer {
  /**
   * 타입 안전성 분석
   */
  public analyzeTypeSafety(
    language: string,
    hasTypeAnnotations: boolean,
    hasCompileTimeChecks: boolean
  ): number {
    let score = 0.5;

    // 언어별 기본 타입 안전성
    const languageTypeSafety: Record<string, number> = {
      // 정적 타입 언어 (높음)
      Rust: 0.95,
      Go: 0.90,
      Java: 0.85,
      Kotlin: 0.85,
      TypeScript: 0.85,
      Swift: 0.88,
      Haskell: 0.90,
      Scala: 0.85,
      OCaml: 0.88,
      // 동적 타입 언어 (낮음)
      Python: 0.65,
      Ruby: 0.60,
      JavaScript: 0.55,
      Lua: 0.50,
      // 중간
      PHP: 0.65,
      Perl: 0.60,
      Clojure: 0.70,
    };

    score = languageTypeSafety[language] || 0.65;

    // 추가 포인트
    if (hasTypeAnnotations) score += 0.10;
    if (hasCompileTimeChecks) score += 0.05;

    return Math.max(0, Math.min(1, score));
  }

  /**
   * 메모리 안전성 분석
   */
  public analyzeMemorySafety(
    language: string,
    hasGarbageCollection: boolean,
    hasBoundsChecking: boolean,
    hasNullSafety: boolean
  ): number {
    let score = 0.5;

    // 언어별 기본 메모리 안전성
    const languageMemorySafety: Record<string, number> = {
      // 자동 메모리 관리 (높음)
      Java: 0.90,
      Python: 0.88,
      Ruby: 0.88,
      JavaScript: 0.85,
      Go: 0.85,
      Kotlin: 0.88,
      // 수동 메모리 관리 (낮음)
      C: 0.30,
      'C++': 0.40,
      // 중간
      Rust: 0.98,  // 소유권 시스템
      Swift: 0.92,
      Haskell: 0.95,
      // 기타
      PHP: 0.80,
      Perl: 0.75,
      Clojure: 0.90,
    };

    score = languageMemorySafety[language] || 0.65;

    // 추가 포인트
    if (hasGarbageCollection) score += 0.05;
    if (hasBoundsChecking) score += 0.05;
    if (hasNullSafety) score += 0.05;

    return Math.max(0, Math.min(1, score));
  }

  /**
   * 동시성 안전성 분석
   */
  public analyzeConcurrencySafety(
    language: string,
    hasChannels: boolean,
    hasActors: boolean,
    hasImmutability: boolean
  ): number {
    let score = 0.5;

    // 언어별 기본 동시성 안전성
    const languageConcurrencySafety: Record<string, number> = {
      // 강력한 동시성 지원 (높음)
      Go: 0.95,
      Erlang: 0.95,
      Elixir: 0.93,
      Rust: 0.92,
      Scala: 0.85,
      Clojure: 0.85,
      // 약한 동시성 (낮음)
      Python: 0.50,  // GIL
      Ruby: 0.55,    // GIL-like
      JavaScript: 0.60,  // 싱글 스레드 + 이벤트 루프
      // 중간
      Java: 0.75,
      Kotlin: 0.75,
      Swift: 0.80,
    };

    score = languageConcurrencySafety[language] || 0.60;

    // 추가 포인트
    if (hasChannels) score += 0.10;
    if (hasActors) score += 0.10;
    if (hasImmutability) score += 0.05;

    return Math.max(0, Math.min(1, score));
  }

  /**
   * 에러 처리 분석
   */
  public analyzeErrorHandling(
    hasExceptionHandling: boolean,
    hasResultType: boolean,
    hasValidation: boolean,
    errorCodeCount: number
  ): number {
    let score = 0.5;

    if (hasExceptionHandling) score += 0.20;
    if (hasResultType) score += 0.20;  // Option/Result 타입
    if (hasValidation) score += 0.15;

    // 에러 코드 개수 (더 많을수록 좋음, 최대 5개)
    score += Math.min(0.15, (errorCodeCount / 5) * 0.15);

    return Math.max(0, Math.min(1, score));
  }

  /**
   * 보안 분석
   */
  public analyzeSecurity(
    language: string,
    hasInputValidation: boolean,
    hasEncryption: boolean,
    hasSQLInjectionProtection: boolean,
    hasXSSProtection: boolean
  ): number {
    let score = 0.5;

    // 언어별 기본 보안 점수
    const languageSecurity: Record<string, number> = {
      // 높은 보안 (강력한 타입 + 메모리 안전)
      Rust: 0.90,
      Go: 0.85,
      // 중간
      Java: 0.75,
      Python: 0.70,
      // 주의 필요
      PHP: 0.60,
      JavaScript: 0.65,
      Perl: 0.55,
    };

    score = languageSecurity[language] || 0.65;

    // 추가 포인트
    if (hasInputValidation) score += 0.10;
    if (hasEncryption) score += 0.10;
    if (hasSQLInjectionProtection) score += 0.10;
    if (hasXSSProtection) score += 0.10;

    return Math.max(0, Math.min(1, score));
  }

  /**
   * 종합 안전도 분석
   */
  public analyzeSafety(params: {
    language: string;
    hasTypeAnnotations: boolean;
    hasCompileTimeChecks: boolean;
    hasGarbageCollection: boolean;
    hasBoundsChecking: boolean;
    hasNullSafety: boolean;
    hasChannels: boolean;
    hasActors: boolean;
    hasImmutability: boolean;
    hasExceptionHandling: boolean;
    hasResultType: boolean;
    hasValidation: boolean;
    errorCodeCount: number;
    hasInputValidation: boolean;
    hasEncryption: boolean;
    hasSQLInjectionProtection: boolean;
    hasXSSProtection: boolean;
  }): SafetyAnalysis {
    const typeSafety = this.analyzeTypeSafety(
      params.language,
      params.hasTypeAnnotations,
      params.hasCompileTimeChecks
    );

    const memorySafety = this.analyzeMemorySafety(
      params.language,
      params.hasGarbageCollection,
      params.hasBoundsChecking,
      params.hasNullSafety
    );

    const concurrencySafety = this.analyzeConcurrencySafety(
      params.language,
      params.hasChannels,
      params.hasActors,
      params.hasImmutability
    );

    const errorHandling = this.analyzeErrorHandling(
      params.hasExceptionHandling,
      params.hasResultType,
      params.hasValidation,
      params.errorCodeCount
    );

    const security = this.analyzeSecurity(
      params.language,
      params.hasInputValidation,
      params.hasEncryption,
      params.hasSQLInjectionProtection,
      params.hasXSSProtection
    );

    const overallSafety = (
      typeSafety +
      memorySafety +
      concurrencySafety +
      errorHandling +
      security
    ) / 5;

    // Verdict 결정
    let verdict: 'safe' | 'caution' | 'risky';
    if (overallSafety >= 0.80) {
      verdict = 'safe';
    } else if (overallSafety >= 0.60) {
      verdict = 'caution';
    } else {
      verdict = 'risky';
    }

    // 권장사항 생성
    const recommendations: string[] = [];

    if (typeSafety < 0.75) {
      recommendations.push('⚠️  타입 안전성: 타입 어노테이션 추가 권장');
    }

    if (memorySafety < 0.75) {
      recommendations.push('⚠️  메모리 안전성: 메모리 관리 검토 필요');
    }

    if (concurrencySafety < 0.75) {
      recommendations.push('⚠️  동시성 안전성: 락/채널 사용 권장');
    }

    if (errorHandling < 0.75) {
      recommendations.push('⚠️  에러 처리: 더 많은 에러 코드 정의 권장');
    }

    if (security < 0.75) {
      recommendations.push('⚠️  보안: 입력 검증 및 암호화 강화 권장');
    }

    if (recommendations.length === 0) {
      recommendations.push('✅ 모든 안전도 지표가 양호합니다.');
    }

    return {
      typeSafety: Math.round(typeSafety * 100) / 100,
      memorySafety: Math.round(memorySafety * 100) / 100,
      concurrencySafety: Math.round(concurrencySafety * 100) / 100,
      errorHandling: Math.round(errorHandling * 100) / 100,
      security: Math.round(security * 100) / 100,
      overallSafety: Math.round(overallSafety * 100) / 100,
      verdict,
      recommendations,
    };
  }

  /**
   * 안전도 리포트 생성 (문자열)
   */
  public generateSafetyReport(analysis: SafetyAnalysis): string {
    const verdictEmoji =
      analysis.verdict === 'safe'
        ? '✅'
        : analysis.verdict === 'caution'
          ? '⚠️'
          : '❌';

    const lines = [
      `${verdictEmoji} 종합 안전도: ${(analysis.overallSafety * 100).toFixed(1)}% (${analysis.verdict.toUpperCase()})`,
      '',
      '상세 분석:',
      `  • 타입 안전성: ${(analysis.typeSafety * 100).toFixed(1)}%`,
      `  • 메모리 안전성: ${(analysis.memorySafety * 100).toFixed(1)}%`,
      `  • 동시성 안전성: ${(analysis.concurrencySafety * 100).toFixed(1)}%`,
      `  • 에러 처리: ${(analysis.errorHandling * 100).toFixed(1)}%`,
      `  • 보안: ${(analysis.security * 100).toFixed(1)}%`,
      '',
      '권장사항:',
      ...analysis.recommendations.map(r => `  ${r}`),
    ];

    return lines.join('\n');
  }
}

export default SafetyAnalyzer;
