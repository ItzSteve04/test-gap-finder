import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AnalyzeResponse } from './analyzer.service';

export interface HistorySummary {
  id: string;
  title: string;
  repository: string;
  source_type: string | null;
  status: 'running' | 'completed' | 'failed';
  error_message: string | null;
  created_at: string;
  updated_at: string;
  python_files: number | null;
  test_files: number | null;
  gaps_count: number | null;
  generated_tests_count: number | null;
  coverage_before: number | null;
  coverage_after: number | null;
  tests_passed: number | null;
  tests_failed: number | null;
}

export type HistoryDetail = HistorySummary & AnalyzeResponse;

@Injectable({ providedIn: 'root' })
export class HistoryService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = 'http://127.0.0.1:8000/history';

  list(query?: string): Observable<{ items: HistorySummary[] }> {
    let params = new HttpParams();
    if (query) params = params.set('q', query);
    return this.http.get<{ items: HistorySummary[] }>(this.baseUrl, { params });
  }

  get(id: string): Observable<HistoryDetail> {
    return this.http.get<HistoryDetail>(`${this.baseUrl}/${id}`);
  }

  rename(id: string, title: string): Observable<{ id: string; title: string }> {
    return this.http.patch<{ id: string; title: string }>(`${this.baseUrl}/${id}`, { title });
  }

  delete(id: string): Observable<{ id: string; deleted: boolean }> {
    return this.http.delete<{ id: string; deleted: boolean }>(`${this.baseUrl}/${id}`);
  }
}
