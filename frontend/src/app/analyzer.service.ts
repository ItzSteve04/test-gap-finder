import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface TestResults {
  passed: number;
  failed: number;
  exit_code: number;
  coverage_before: number;
  coverage_after: number;
  stdout: string;
  stderr: string;
  execution_skipped?: boolean;
}

export interface GapRecord {
  function: string;
  qualified_name: string;
  source_file: string;
  covering_tests: string[];
  missing_branches: string[];
  missing_exceptions: string[];
  confidence: string;
  confidence_label: string;
  reason: string;
}

export interface GeneratedTest {
  function: string;
  gap: string;
  code: string;
}

export interface AnalyzeResponse {
  id: string;
  title: string;
  created_at: string;
  repository: string;
  status: string;
  python_files: number;
  test_files: number;
  has_tests_folder: boolean;
  gaps: GapRecord[];
  generated_tests: GeneratedTest[];
  test_results: TestResults;
}

@Injectable({ providedIn: 'root' })
export class AnalyzerService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = 'http://127.0.0.1:8000/analyze';

  analyze(repositoryUrl: string): Observable<AnalyzeResponse> {
    return this.http.post<AnalyzeResponse>(this.apiUrl, { repository_url: repositoryUrl });
  }
}
