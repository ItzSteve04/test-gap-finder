import {
  Component,
  input,
  output,
  signal,
  computed,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { HistorySummary } from '../history.service';

export interface BucketedGroup {
  label: string;
  items: HistorySummary[];
}

function getBucketLabel(dateStr: string): string {
  const now = new Date();
  const d = new Date(dateStr);
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterdayStart = new Date(todayStart);
  yesterdayStart.setDate(todayStart.getDate() - 1);
  const sevenDaysAgo = new Date(todayStart);
  sevenDaysAgo.setDate(todayStart.getDate() - 7);

  if (d >= todayStart) return 'Today';
  if (d >= yesterdayStart) return 'Yesterday';
  if (d >= sevenDaysAgo) return 'Previous 7 Days';
  return 'Older';
}

const BUCKET_ORDER = ['Today', 'Yesterday', 'Previous 7 Days', 'Older'];

@Component({
  selector: 'app-history-sidebar',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    FormsModule,
    MatIconModule,
    MatButtonModule,
    MatMenuModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
  ],
  templateUrl: './history-sidebar.html',
  styleUrl: './history-sidebar.scss',
})
export class HistorySidebarComponent {
  items = input.required<HistorySummary[]>();
  activeId = input<string | null>(null);
  loading = input(false);

  search = output<string>();
  select = output<string>();
  rename = output<{ id: string; title: string }>();
  delete = output<string>();
  newAnalysis = output<void>();

  /** Per-row editing state: which row is currently being renamed. */
  editingId = signal<string | null>(null);
  editingTitle = signal('');

  buckets = computed<BucketedGroup[]>(() => {
    const grouped = new Map<string, HistorySummary[]>();
    for (const item of this.items()) {
      const label = getBucketLabel(item.created_at);
      if (!grouped.has(label)) grouped.set(label, []);
      grouped.get(label)!.push(item);
    }
    return BUCKET_ORDER
      .filter(label => grouped.has(label))
      .map(label => ({ label, items: grouped.get(label)! }));
  });

  onSearchInput(event: Event): void {
    this.search.emit((event.target as HTMLInputElement).value);
  }

  onRowClick(id: string): void {
    if (this.editingId() === id) return;
    this.select.emit(id);
  }

  startRename(item: HistorySummary, event: MouseEvent): void {
    event.stopPropagation();
    this.editingId.set(item.id);
    this.editingTitle.set(item.title);
  }

  commitRename(id: string): void {
    const title = this.editingTitle().trim();
    if (title) {
      this.rename.emit({ id, title });
    }
    this.editingId.set(null);
  }

  cancelRename(): void {
    this.editingId.set(null);
  }

  onRenameKeydown(event: KeyboardEvent, id: string): void {
    if (event.key === 'Enter') {
      this.commitRename(id);
    } else if (event.key === 'Escape') {
      this.cancelRename();
    }
  }

  onDeleteClick(id: string, event: MouseEvent): void {
    event.stopPropagation();
    this.delete.emit(id);
  }
}
