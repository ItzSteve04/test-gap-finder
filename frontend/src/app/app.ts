import { Component, signal, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { AnalyzerService, AnalyzeResponse } from './analyzer.service';

@Component({
  selector: 'app-root',
  imports: [
    FormsModule,
    CommonModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatIconModule,
    MatExpansionModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  private readonly analyzerService = inject(AnalyzerService);
  private readonly snackBar = inject(MatSnackBar);

  repoPath = '';
  loading = signal(false);
  result = signal<AnalyzeResponse | null>(null);

  analyze(): void {
    const path = this.repoPath.trim();
    if (!path) return;

    this.loading.set(true);
    this.result.set(null);

    this.analyzerService.analyze(path).subscribe({
      next: (data) => {
        this.result.set(data);
        this.loading.set(false);
      },
      error: (err) => {
        const msg = err?.error?.detail ?? err?.message ?? 'An unexpected error occurred.';
        this.snackBar.open(msg, 'Dismiss', { duration: 8000 });
        this.loading.set(false);
      }
    });
  }
}
