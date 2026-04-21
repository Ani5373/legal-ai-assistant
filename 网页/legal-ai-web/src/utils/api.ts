import type { CaseAnalysisResponse } from '../types/analysis';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8111';

export async function analyzeCase(text: string, caseId?: string): Promise<CaseAnalysisResponse> {
  const response = await fetch(`${API_BASE_URL}/api/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, case_id: caseId }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    // 兼容 FastAPI 错误结构，优先读取 detail，其次 message，最后 HTTP 状态码
    const errorMessage = error.detail || error.message || `HTTP ${response.status}`;
    throw new Error(errorMessage);
  }

  return response.json();
}

export interface StreamChunk {
  type: 'start' | 'stage' | 'fact_extraction_complete' | 'charge_prediction_complete' | 
        'law_retrieval_complete' | 'complete' | 'error' | 'done';
  stage?: string;
  message?: string;
  data?: any;
  case_id?: string;
  risk_level?: string;
}

export async function analyzeCaseStream(
  text: string,
  caseId: string | undefined,
  onChunk: (chunk: StreamChunk) => void
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/analyze/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, case_id: caseId }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    const errorMessage = error.detail || error.message || `HTTP ${response.status}`;
    throw new Error(errorMessage);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('无法读取响应流');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      
      // 处理 SSE 格式的数据
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data.trim()) {
            try {
              const chunk = JSON.parse(data) as StreamChunk;
              onChunk(chunk);
            } catch (e) {
              console.error('解析 SSE 数据失败:', e, data);
            }
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
