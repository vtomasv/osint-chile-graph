/**
 * Diseño seleccionado: Cartografía forense neo-brutalista chilena.
 * Este cliente API mantiene la estación de trabajo conectada al backend local,
 * reforzando trazabilidad, evidencia y separación entre automatización y human-in-the-loop.
 */

export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export type Investigation = {
  id: string;
  title: string;
  objective: string;
  status: string;
  created_at?: string;
};

export type Transform = {
  id: string;
  name: string;
  description: string;
  input_types: string[];
  output_types: string[];
  execution_mode: "automatic" | "human_in_the_loop" | "blocked";
  risk_level: "low" | "medium" | "high";
  requires_human: boolean;
  source_policy: string;
};

export type GraphNode = {
  id: string;
  type: string;
  label: string;
  value: string;
  properties: Record<string, unknown>;
  confidence: number;
};

export type GraphEdge = {
  id: string;
  source: string;
  target: string;
  type: string;
  properties: Record<string, unknown>;
  confidence: number;
};

export type FindingRelationship = {
  id: string;
  type: string;
  source_id: string;
  source_label: string;
  target_id: string;
  target_label: string;
  properties: Record<string, unknown>;
  confidence: number;
};

export type EvidenceItem = {
  id: string;
  source_name: string;
  source_url: string;
  extract: string;
  confidence: number;
  properties: Record<string, unknown>;
  created_at: string;
};

export type HumanTaskItem = {
  id: string;
  label: string;
  value: string;
  properties: Record<string, unknown>;
  confidence: number;
};

export type TransformRunItem = {
  id: string;
  transform_id: string;
  input_type: string;
  input_value: string;
  created_at: string;
  output_summary: { entities: number; human_tasks: number; relationships: number };
};

export type TimelineItem = {
  at: string;
  kind: string;
  title: string;
  detail: string;
  confidence: number;
};

export type FindingsReport = {
  investigation: Investigation;
  summary: {
    entities: number;
    relationships: number;
    evidence: number;
    human_tasks: number;
    transform_runs: number;
    average_confidence: number;
    entity_types: Record<string, number>;
    evidence_by_source: Record<string, number>;
  };
  entities: GraphNode[];
  relationships: FindingRelationship[];
  evidence: EvidenceItem[];
  human_tasks: HumanTaskItem[];
  runs: TransformRunItem[];
  timeline: TimelineItem[];
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; ai_provider: string; ollama_base_url: string }>("/health"),
  investigations: () => request<Investigation[]>("/api/investigations"),
  transforms: () => request<Transform[]>("/api/transforms"),
  graph: (investigationId: string) => request<{ nodes: GraphNode[]; edges: GraphEdge[] }>(`/api/graph/${investigationId}`),
  findings: (investigationId: string) => request<FindingsReport>(`/api/investigations/${investigationId}/findings`),
  addSeed: (payload: { investigation_id: string; input_type: string; value: string }) =>
    request<GraphNode>("/api/seeds", { method: "POST", body: JSON.stringify(payload) }),
  runTransform: (payload: { investigation_id: string; transform_id: string; input_type: string; value: string }) =>
    request<{ run_id: string; output: unknown; created_entities: GraphNode[] }>("/api/transforms/run", { method: "POST", body: JSON.stringify(payload) }),
  aiRun: (payload: { prompt_id: string; variables: Record<string, unknown>; provider?: string; model?: string }) =>
    request<{ provider: string; model: string; content: string }>("/api/ai/run", { method: "POST", body: JSON.stringify(payload) }),
};
