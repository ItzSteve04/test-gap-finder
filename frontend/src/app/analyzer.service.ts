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
}

export interface AnalyzeResponse {
  repository: string;
  status: string;
  python_files: number;
  test_files: number;
  has_tests_folder: boolean;
  gaps: string[];
  generated_tests: string[];
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
