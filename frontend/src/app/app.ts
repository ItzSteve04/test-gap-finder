import { Component, signal, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { AnalyzerService, AnalyzeResponse } from './analyzer.service';

@Component({
  selector: 'app-root',
  imports: [FormsModule, CommonModule],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  private readonly analyzerService = inject(AnalyzerService);

  repoPath = '';
  loading = signal(false);
  error = signal<string | null>(null);
  result = signal<AnalyzeResponse | null>(null);

  analyze(): void {
    const path = this.repoPath.trim();
    if (!path) return;

    this.loading.set(true);
    this.error.set(null);
    this.result.set(null);

    this.analyzerService.analyze(path).subscribe({
      next: (data) => {
        this.result.set(data);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(err?.error?.detail ?? err?.message ?? 'An unexpected error occurred.');
        this.loading.set(false);
      }
    });
  }
}
