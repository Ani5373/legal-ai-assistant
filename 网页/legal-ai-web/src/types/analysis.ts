export interface ChargePrediction {
  label: string;
  probability: number;
  source: string;
  rank?: number;
}

export interface GraphNode {
  id: string;
  type: string;
  label: string;
  description: string;
  source: string;
  metadata: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
  evidence: string;
  metadata: Record<string, unknown>;
}

export interface ExecutionStep {
  id: string;
  name: string;
  agent: string;
  status: 'completed' | 'failed' | 'skipped';
  started_at: string;
  ended_at: string;
  summary: string;
  output_keys: string[];
  details: Record<string, unknown>;
}

export interface SimilarCase {
  case_id: string;
  text: string;
  charges: string[];
  similarity_score: number;
}

export interface CaseAnalysisResponse {
  contract_version: string;
  case_id: string;
  text: string;
  predictions: ChargePrediction[];
  nodes: GraphNode[];
  edges: GraphEdge[];
  steps: ExecutionStep[];
  report: string;
  metadata: Record<string, unknown>;
  warnings: string[];
}
