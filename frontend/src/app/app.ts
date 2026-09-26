import {
  Component,
  signal,
  inject,
  OnInit,
  afterNextRender,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged, switchMap } from 'rxjs/operators';
import { ActivatedRoute, Router } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { AnalyzerService, AnalyzeResponse } from './analyzer.service';
import { HistoryService, HistorySummary } from './history.service';
import { HistorySidebarComponent } from './history-sidebar/history-sidebar';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    FormsModule,
    CommonModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatIconModule,
    MatToolbarModule,
    MatExpansionModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MatSidenavModule,
    HistorySidebarComponent,
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App implements OnInit {
  private readonly analyzerService = inject(AnalyzerService);
  private readonly historyService = inject(HistoryService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  readonly currentYear = new Date().getFullYear();
  repoPath = '';
  loading = signal(false);
  result = signal<AnalyzeResponse | null>(null);

  historyItems = signal<HistorySummary[]>([]);
  historyLoading = signal(false);
  activeId = signal<string | null>(null);
  isMobile = signal(false);

  private readonly historySearch$ = new Subject<string>();

  constructor() {
    // Debounced server-side search
    this.historySearch$
      .pipe(
        debounceTime(300),
        distinctUntilChanged(),
        switchMap(q => this.historyService.list(q || undefined)),
        takeUntilDestroyed(),
      )
      .subscribe(res => this.historyItems.set(res.items));

    // Set up mobile breakpoint listener (zoneless-safe: call signal.set directly)
    afterNextRender(() => {
      const mq = window.matchMedia('(max-width: 600px)');
      this.isMobile.set(mq.matches);
      mq.addEventListener('change', e => this.isMobile.set(e.matches));
    });
  }

  ngOnInit(): void {
    this.refreshHistory();

    // Deep-link: if URL contains /analysis/:id, load that entry
    this.route.paramMap.subscribe(params => {
      const id = params.get('id');
      if (id) {
        this.activeId.set(id);
        this.historyService.get(id).subscribe({
          next: detail => this.result.set(detail),
          error: () => { /* entry may no longer exist, just ignore */ },
        });
      }
    });
  }

  refreshHistory(query?: string): void {
    this.historyLoading.set(true);
    this.historyService.list(query).subscribe({
      next: res => {
        this.historyItems.set(res.items);
        this.historyLoading.set(false);
      },
      error: () => this.historyLoading.set(false),
    });
  }

  analyze(): void {
    const path = this.repoPath.trim();
    if (!path) return;

    this.loading.set(true);
    this.result.set(null);

    // Optimistic "running" row — appears immediately, before the backend responds
    const placeholderId = `pending-${Date.now()}`;
    const placeholder: HistorySummary = {
      id: placeholderId,
      title: path.replace(/\\/g, '/').split('/').filter(Boolean).pop() || path,
      repository: path,
      source_type: null,
      status: 'running',
      error_message: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      python_files: null,
      test_files: null,
      gaps_count: null,
      generated_tests_count: null,
      coverage_before: null,
      coverage_after: null,
      tests_passed: null,
      tests_failed: null,
    };
    this.historyItems.update(items => [placeholder, ...items]);
    this.activeId.set(placeholderId);

    this.analyzerService.analyze(path).subscribe({
      next: (data) => {
        this.result.set(data);
        this.activeId.set(data.id);
        this.loading.set(false);
        this.router.navigate(['/analysis', data.id]);
        this.refreshHistory();
      },
      error: (err) => {
        const msg = err?.error?.detail ?? err?.message ?? 'An unexpected error occurred.';
        this.snackBar.open(msg, 'Dismiss', { duration: 8000 });
        this.loading.set(false);
        this.refreshHistory(); // failed entry is now in the DB
      },
    });
  }

  onHistorySearch(value: string): void {
    this.historySearch$.next(value);
  }

  onSelectHistoryItem(id: string): void {
    if (id.startsWith('pending-')) return;
    this.activeId.set(id);
    this.router.navigate(['/analysis', id]);
    this.historyService.get(id).subscribe(detail => this.result.set(detail));
  }

  onNewAnalysis(): void {
    this.repoPath = '';
    this.result.set(null);
    this.activeId.set(null);
    this.router.navigate(['/']);
  }

  onRenameHistoryItem(e: { id: string; title: string }): void {
    this.historyService.rename(e.id, e.title).subscribe(() => this.refreshHistory());
  }

  onDeleteHistoryItem(id: string): void {
    this.historyService.delete(id).subscribe(() => {
      this.historyItems.update(items => items.filter(i => i.id !== id));
      if (this.activeId() === id) {
        this.onNewAnalysis();
      }
    });
  }
}
