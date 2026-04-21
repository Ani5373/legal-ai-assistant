import type { CaseAnalysisResponse, ChargePrediction } from '../types/analysis';

const HISTORY_KEY = 'caseHistory';
const MAX_HISTORY = 50;

export interface AnalysisHistory {
  id: number;
  text: string;
  case_id: string;
  predictions: ChargePrediction[];
  report_preview: string;
  warning_count: number;
  timestamp: string;
  // 保存完整的分析数据
  fullAnalysis: CaseAnalysisResponse;
}

export function saveToHistory(analysis: CaseAnalysisResponse): void {
  const history = getHistory();
  const newRecord: AnalysisHistory = {
    id: Date.now(),
    text: analysis.text.slice(0, 200),
    case_id: analysis.case_id,
    predictions: analysis.predictions,
    report_preview: analysis.report.slice(0, 300),
    warning_count: analysis.warnings.length,
    timestamp: new Date().toISOString(),
    fullAnalysis: analysis, // 保存完整数据
  };
  history.push(newRecord);
  if (history.length > MAX_HISTORY) {
    history.splice(0, history.length - MAX_HISTORY);
  }
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
}

export function getHistory(): AnalysisHistory[] {
  const saved = localStorage.getItem(HISTORY_KEY);
  if (!saved) return [];
  try {
    return JSON.parse(saved);
  } catch {
    return [];
  }
}

export function getHistoryById(id: number): AnalysisHistory | null {
  const history = getHistory();
  return history.find(item => item.id === id) || null;
}

export function clearHistory(): void {
  localStorage.removeItem(HISTORY_KEY);
}

export function deleteHistoryById(id: number): void {
  const history = getHistory();
  const newHistory = history.filter(item => item.id !== id);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(newHistory));
}
