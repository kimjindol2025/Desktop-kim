/**
 * Metadata Store
 *
 * 패턴 메타데이터를 파일 시스템에 저장/로드
 * JSON Lines 형식 사용
 */

import * as fs from 'fs';
import * as path from 'path';
import PatternVectorIndex, { PatternVector } from './pattern-vector-index';

export interface MetadataRecord {
  id: string;
  language: string;
  operation: string;
  file_path: string;
  lines_of_code: number;
  vector: number[];
  metadata: {
    performance: number;
    memory: number;
    concurrency: number;
    testing: number;
    ecosystem: number;
    real_world: number;
    best_practices: number;
  };
  error_codes: number[];
  complexity: string;
}

export class MetadataStore {
  private filePath: string;
  private index: PatternVectorIndex;

  constructor(filePath: string, vectorDimension: number = 7) {
    this.filePath = filePath;
    this.index = new PatternVectorIndex(vectorDimension, 0.3);
  }

  /**
   * JSON Lines 파일에서 메타데이터 로드
   */
  public load(): number {
    if (!fs.existsSync(this.filePath)) {
      console.warn(`File not found: ${this.filePath}`);
      return 0;
    }

    const content = fs.readFileSync(this.filePath, 'utf-8');
    const lines = content.trim().split('\n').filter(line => line.trim());

    let loadedCount = 0;

    for (const line of lines) {
      try {
        const record: MetadataRecord = JSON.parse(line);
        const pattern: PatternVector = {
          id: record.id,
          language: record.language,
          operation: record.operation,
          vector: new Float32Array(record.vector),
          metadata: record.metadata,
        };

        this.index.add(pattern);
        loadedCount++;
      } catch (error) {
        console.error(`Failed to parse line: ${line.substring(0, 50)}...`);
      }
    }

    console.log(`Loaded ${loadedCount} records from ${this.filePath}`);
    return loadedCount;
  }

  /**
   * 메타데이터를 JSON Lines 형식으로 저장
   */
  public save(records: MetadataRecord[]): void {
    const lines = records.map(record => JSON.stringify(record)).join('\n');

    fs.writeFileSync(this.filePath, lines + '\n', 'utf-8');
    console.log(`Saved ${records.length} records to ${this.filePath}`);
  }

  /**
   * 단일 메타데이터 추가
   */
  public addRecord(record: MetadataRecord): void {
    const pattern: PatternVector = {
      id: record.id,
      language: record.language,
      operation: record.operation,
      vector: new Float32Array(record.vector),
      metadata: record.metadata,
    };

    this.index.add(pattern);

    // 파일에 추가 (append mode)
    const line = JSON.stringify(record);
    fs.appendFileSync(this.filePath, line + '\n', 'utf-8');
  }

  /**
   * VectorIndex 접근
   */
  public getIndex(): PatternVectorIndex {
    return this.index;
  }

  /**
   * 통계
   */
  public getStats() {
    const stats = this.index.getStats();
    return {
      ...stats,
      languages: Array.from(stats.languages),
      operations: Array.from(stats.operations),
    };
  }
}

export default MetadataStore;
