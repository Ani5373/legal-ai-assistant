import type { SimilarCase } from '../types/analysis';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8111';

export async function fetchSimilarCases(charges: string[], limit: number = 3): Promise<SimilarCase[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/similar-cases`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ charges, limit }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data.similar_cases || [];
  } catch (error) {
    console.error('获取类案推荐失败:', error);
    return [];
  }
}
