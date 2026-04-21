export function formatProbability(prob: number): string {
  return `${(prob * 100).toFixed(1)}%`;
}

export function calculateDuration(startedAt: string, endedAt: string): number {
  return new Date(endedAt).getTime() - new Date(startedAt).getTime();
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}min`;
}

export function getStatusColor(status: 'completed' | 'failed' | 'skipped'): string {
  switch (status) {
    case 'completed': return 'text-emerald-400';
    case 'failed': return 'text-red-400';
    case 'skipped': return 'text-amber-400';
  }
}

export function getStatusBgColor(status: 'completed' | 'failed' | 'skipped'): string {
  switch (status) {
    case 'completed': return 'bg-emerald-500/20';
    case 'failed': return 'bg-red-500/20';
    case 'skipped': return 'bg-amber-500/20';
  }
}
