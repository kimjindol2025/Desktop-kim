/**
 * Verdict Generator
 *
 * AI 최종 판정 생성
 *
 * 종합 정보:
 *   • 안전도 분석
 *   • 성능 예측
 *   • 생태계 평가
 *   • 모범사례 준수도
 *   • 카운터 예제
 */

import { SafetyAnalysis } from './safety-analyzer';
import { FinalScoreResult } from './multi-heuristic';

export interface AIVerdict {
  verdict: string;
  safetyLevel: 'safe' | 'caution' | 'risky';
  overallScore: number;
  components: {
    safety: number;
    performance: number;
    ecosystem: number;
    bestPractices: number;
  };
  recommendations: string[];
  counterexamples: string[];
  references: string[];
}

export class VerdictGenerator {
  /**
   * 성능 판정
   */
  private generatePerformanceVerdic(
    performanceScore: number,
    linesOfCode: number
  ): { verdict: string; score: number; recommendations: string[] } {
    const recommendations: string[] = [];
    let score = performanceScore;

    if (performanceScore >= 0.90) {
      const verdict = '⚡ 매우 빠름';
      if (linesOfCode > 50) {
        recommendations.push('구현이 크지만 성능이 우수합니다');
      }
      return { verdict, score, recommendations };
    } else if (performanceScore >= 0.75) {
      recommendations.push('성능 최적화 가능성 있음');
      return { verdict: '✅ 양호', score, recommendations };
    } else if (performanceScore >= 0.60) {
      recommendations.push('성능 개선 권장');
      score -= 0.10;
      return { verdict: '⚠️  중간', score, recommendations };
    } else {
      recommendations.push('성능 최적화 필수');
      score -= 0.20;
      return { verdict: '❌ 느림', score, recommendations };
    }
  }

  /**
   * 생태계 평가
   */
  private generateEcosystemVerdic(
    ecosystemScore: number,
    language: string
  ): { verdict: string; score: number; recommendations: string[] } {
    const recommendations: string[] = [];
    let score = ecosystemScore;

    // 언어별 생태계 평가
    const ecosystemInfo: Record<string, string> = {
      Python: '📚 매우 풍부한 라이브러리 생태계',
      JavaScript: '📚 npm 패키지 생태계가 매우 발달',
      Java: '📚 엔터프라이즈급 라이브러리 풍부',
      Go: '⭐ 표준 라이브러리가 포괄적',
      Rust: '📦 활발하게 성장하는 crates.io',
      Ruby: '💎 RubyGems 생태계 잘 정비',
      PHP: '📦 Composer 패키지 풍부',
      Kotlin: '☕ Java 생태계와 호환',
    };

    const info = ecosystemInfo[language] || '📚 기본 라이브러리 지원';

    if (ecosystemScore >= 0.85) {
      recommendations.push(`${info} - 외부 라이브러리 활용 권장`);
      return { verdict: '✅ 우수', score, recommendations };
    } else if (ecosystemScore >= 0.70) {
      recommendations.push(`${info}`);
      return { verdict: '✅ 양호', score, recommendations };
    } else {
      recommendations.push(`${info} - 표준 라이브러리 활용 권장`);
      return { verdict: '⚠️  제한적', score, recommendations };
    }
  }

  /**
   * 모범사례 준수도 계산
   */
  private calculateBestPracticesScore(
    safety: number,
    performance: number,
    ecosystem: number,
    ecosystem_score: number
  ): number {
    // 모범사례 = (안전도 + 성능 + 생태계 + 에코시스템) / 4
    return (safety + performance + ecosystem + ecosystem_score) / 4;
  }

  /**
   * 카운터 예제 생성
   */
  private generateCounterexamples(
    language: string,
    operation: string,
    safetyAnalysis: SafetyAnalysis
  ): string[] {
    const counterexamples: string[] = [];

    // 언어/연산별 일반적인 실수
    const antiPatterns: Record<string, string[]> = {
      'Ruby/read.file': [
        '❌ File.read() - 전체 메모리 로드',
        '⚠️  readlines() - 배열 생성 오버헤드',
      ],
      'Python/read.file': [
        '❌ 전체 파일을 메모리로 읽기',
        '⚠️  인코딩 에러 처리 없음',
      ],
      'Java/filter': [
        '❌ ArrayList에 모든 요소 추가 후 필터링',
        '⚠️  병렬 스트림 과다 사용',
      ],
      'Go/filter': [
        '❌ make()로 크기 지정 없이 슬라이스 생성',
        '⚠️  goroutine 누수',
      ],
    };

    const key = `${language}/${operation}`;
    const patterns = antiPatterns[key] || [
      '❌ 예외 처리 없음',
      '⚠️  성능 최적화 없음',
    ];

    counterexamples.push('피해야 할 패턴:');
    patterns.forEach(p => counterexamples.push(`  ${p}`));

    // 안전도 기반 추가 경고
    if (safetyAnalysis.typeSafety < 0.70) {
      counterexamples.push('  ❌ 타입 체크 없이 사용');
    }

    if (safetyAnalysis.errorHandling < 0.70) {
      counterexamples.push('  ❌ 에러 처리 누락');
    }

    return counterexamples;
  }

  /**
   * 참고 자료 생성
   */
  private generateReferences(
    language: string,
    operation: string
  ): string[] {
    const references: string[] = [];

    // 언어별 공식 문서
    const docs: Record<string, string> = {
      Ruby: 'https://ruby-doc.org/core/File.html',
      Python: 'https://docs.python.org/3/library/io.html',
      Java: 'https://docs.oracle.com/en/java/javase/',
      Go: 'https://golang.org/pkg/io/',
      Rust: 'https://doc.rust-lang.org/std/fs/',
    };

    // 패턴별 가이드
    if (operation === 'read.file') {
      references.push('📖 VHDL-Analysis/docs/phase3/02_MEMORY_MANAGEMENT.md');
      references.push('📖 Language-Library-Examples (해당 언어)');
    } else if (operation === 'filter') {
      references.push('📖 VHDL-Analysis/docs/phase3/07_BEST_PRACTICES_PATTERNS.md');
    }

    // 언어 문서
    if (docs[language]) {
      references.push(`📚 ${language} 공식 문서: ${docs[language]}`);
    }

    return references;
  }

  /**
   * 종합 AI Verdict 생성
   */
  public generateVerdict(params: {
    language: string;
    operation: string;
    heuristicScore: FinalScoreResult;
    safetyAnalysis: SafetyAnalysis;
    lines_of_code: number;
  }): AIVerdict {
    const { language, operation, heuristicScore, safetyAnalysis, lines_of_code } = params;

    // 각 컴포넌트 점수
    const components = {
      safety: safetyAnalysis.overallSafety,
      performance: heuristicScore.performanceScore,
      ecosystem: 0,  // 별도로 계산
      bestPractices: 0,
    };

    // 생태계 점수 (언어별 고정값)
    const ecosystemScores: Record<string, number> = {
      Python: 0.95,
      JavaScript: 0.92,
      Java: 0.90,
      Go: 0.88,
      Rust: 0.85,
      Ruby: 0.85,
      Kotlin: 0.82,
      Swift: 0.80,
      PHP: 0.78,
      Scala: 0.75,
    };
    components.ecosystem = ecosystemScores[language] || 0.70;

    // 모범사례 점수
    components.bestPractices = this.calculateBestPracticesScore(
      components.safety,
      components.performance,
      components.ecosystem,
      heuristicScore.performanceScore
    );

    // 종합 점수
    const overallScore =
      components.safety * 0.30 +
      components.performance * 0.25 +
      components.ecosystem * 0.20 +
      components.bestPractices * 0.25;

    // 최종 판정
    let safetyLevel: 'safe' | 'caution' | 'risky' = safetyAnalysis.verdict;
    let verdict = '';

    if (overallScore >= 0.85) {
      verdict = '✅ 강력 권장';
    } else if (overallScore >= 0.75) {
      verdict = '✅ 권장';
    } else if (overallScore >= 0.65) {
      verdict = '⚠️  조건부 권장';
    } else {
      verdict = '❌ 비권장';
    }

    // 권장사항 수집
    const recommendations: string[] = [];

    // 성능 권장사항
    const perfVerdic = this.generatePerformanceVerdic(components.performance, lines_of_code);
    recommendations.push(`성능: ${perfVerdic.verdict}`);
    recommendations.push(...perfVerdic.recommendations);

    // 생태계 권장사항
    const ecosystemVerdic = this.generateEcosystemVerdic(components.ecosystem, language);
    recommendations.push(`생태계: ${ecosystemVerdic.verdict}`);
    recommendations.push(...ecosystemVerdic.recommendations);

    // 안전도 권장사항
    recommendations.push(...safetyAnalysis.recommendations);

    // 카운터 예제
    const counterexamples = this.generateCounterexamples(
      language,
      operation,
      safetyAnalysis
    );

    // 참고 자료
    const references = this.generateReferences(language, operation);

    return {
      verdict,
      safetyLevel,
      overallScore: Math.round(overallScore * 100) / 100,
      components: {
        safety: Math.round(components.safety * 100) / 100,
        performance: Math.round(components.performance * 100) / 100,
        ecosystem: Math.round(components.ecosystem * 100) / 100,
        bestPractices: Math.round(components.bestPractices * 100) / 100,
      },
      recommendations,
      counterexamples,
      references,
    };
  }

  /**
   * Verdict를 보기 좋은 형식으로 출력
   */
  public formatVerdictReport(verdict: AIVerdict): string {
    const lines = [
      `${'═'.repeat(60)}`,
      `${verdict.verdict}`,
      `종합 점수: ${(verdict.overallScore * 100).toFixed(1)}%`,
      `${'═'.repeat(60)}`,
      '',
      '📊 상세 점수:',
      `  • 안전도: ${(verdict.components.safety * 100).toFixed(1)}%`,
      `  • 성능: ${(verdict.components.performance * 100).toFixed(1)}%`,
      `  • 생태계: ${(verdict.components.ecosystem * 100).toFixed(1)}%`,
      `  • 모범사례: ${(verdict.components.bestPractices * 100).toFixed(1)}%`,
      '',
      '💡 권장사항:',
      ...verdict.recommendations.map(r => `  ${r}`),
      '',
      '❌ 피해야 할 패턴:',
      ...verdict.counterexamples.map(c => `  ${c}`),
      '',
      '📚 참고 자료:',
      ...verdict.references.map(r => `  ${r}`),
      `${'═'.repeat(60)}`,
    ];

    return lines.join('\n');
  }
}

export default VerdictGenerator;
