const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type HealthResponse = {
  status: string;
  timestamp: string;
};

export type ChatMessageResponse = {
  session_id: string | null;
  answer: string;
  sources: Array<{ type: string; title: string; url: string | null }>;
};

export type AnalysisSummaryResponse = {
  days: number;
  total_pages: number;
  total_features: number;
  recent_updates: number;
  top_keywords: Array<{ keyword: string; count: number }>;
  activity_trend: Array<{ label: string; value: number }>;
};

export type ConfluencePage = {
  id: string;
  title: string;
  excerpt?: string;
  url?: string;
  space_key?: string;
  author_name?: string;
  updated_at?: string | null;
};

export type AhaFeature = {
  id: string;
  reference_num?: string;
  name: string;
  description?: string;
  status?: string;
  priority?: string | number;
  category?: string;
  source_type?: string;
  url?: string;
};

export type AhaFeaturePage = {
  items: AhaFeature[];
  meta: { limit: number; offset: number; total: number; has_more: boolean };
};

export type CosmosContainerInfo = {
  id: string;
  partition_key_paths: string[];
  default_ttl?: number | null;
  analytical_storage_ttl?: number | null;
};

export type CosmosDiagnosticsRequest = {
  container_name: string;
  query_text: string;
  partition_key_value?: string | null;
  logical_type?: string | null;
  max_items?: number;
  perform_sample_insert?: boolean;
  cleanup_after_insert?: boolean;
  insert_scenarios?: Array<{
    purpose: string;
    payload: Record<string, unknown>;
    partition_key_value?: string | null;
    logical_type?: string | null;
    cleanup_after_insert?: boolean | null;
  }>;
};

export type CosmosDiagnosticsResponse = {
  container_name: string;
  database_name: string;
  logical_type?: string | null;
  query_text: string;
  partition_key_field?: string | null;
  partition_key_value?: string | null;
  result_count: number;
  query_metrics: {
    request_charge: number;
    duration_ms: number;
    activity_id?: string | null;
    query_metrics?: string | null;
    index_metrics?: string | null;
    status_code?: number | null;
  };
  insert_metrics?: {
    purpose?: string | null;
    inserted: boolean;
    cleaned_up: boolean;
    item_id?: string | null;
    source_item_id?: string | null;
    source_item_type?: string | null;
    partition_key_field?: string | null;
    partition_key_value?: string | null;
    request_charge: number;
    delete_request_charge: number;
    create_response_headers: Record<string, unknown>;
    delete_response_headers: Record<string, unknown>;
    inserted_document?: Record<string, unknown> | null;
    status: string;
    error_message?: string | null;
  } | null;
  insert_scenarios: Array<{
    purpose?: string | null;
    inserted: boolean;
    cleaned_up: boolean;
    item_id?: string | null;
    source_item_id?: string | null;
    source_item_type?: string | null;
    partition_key_field?: string | null;
    partition_key_value?: string | null;
    request_charge: number;
    delete_request_charge: number;
    create_response_headers: Record<string, unknown>;
    delete_response_headers: Record<string, unknown>;
    inserted_document?: Record<string, unknown> | null;
    status: string;
    error_message?: string | null;
  }>;
  index_summary: {
    included_path_count: number;
    excluded_path_count: number;
    composite_index_count: number;
    spatial_index_count: number;
    vector_index_count: number;
    indexing_mode?: string | null;
    automatic?: boolean | null;
  };
  size_estimate: {
    sample_count: number;
    average_document_bytes: number;
    largest_document_bytes: number;
    two_mb_limit_bytes: number;
    remaining_bytes_to_two_mb_for_largest_document: number;
  };
  sample_documents: Array<Record<string, unknown>>;
  tuning_recommendations: string[];
};

export type CosmosAssistantRequest = {
  action: string;
  prompt: string;
  container_name: string;
  logical_type?: string | null;
  partition_key_field?: string | null;
  partition_key_value?: string | null;
  current_query?: string | null;
  diagnostics_result?: Record<string, unknown> | null;
};

export type CosmosAssistantResponse = {
  answer: string;
  suggested_query?: string | null;
  follow_up_questions: string[];
};

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/health`);
  if (!response.ok) {
    throw new Error("Failed to fetch health");
  }
  return response.json() as Promise<HealthResponse>;
}

export async function fetchChatSuggestions(limit = 5): Promise<string[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/chat/suggestions?limit=${limit}`);
    if (!response.ok) return [];
    const payload = (await response.json()) as { suggestions: string[] };
    return payload.suggestions ?? [];
  } catch {
    return [];
  }
}

export async function sendChatMessage(
  message: string,
  sessionId?: string,
  context?: { title?: string; hint?: string }
): Promise<ChatMessageResponse> {
  const response = await fetch(`${API_BASE_URL}/api/chat/message`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message,
      session_id: sessionId ?? null,
      context_title: context?.title ?? null,
      context_hint: context?.hint ?? null,
    }),
  });
  if (!response.ok) {
    throw new Error("Failed to send chat message");
  }
  return response.json() as Promise<ChatMessageResponse>;
}

export async function fetchAnalysisSummary(days = 7): Promise<AnalysisSummaryResponse> {
  const response = await fetch(`${API_BASE_URL}/api/analysis/summary?days=${days}`);
  if (!response.ok) {
    throw new Error("Failed to fetch summary");
  }
  return response.json() as Promise<AnalysisSummaryResponse>;
}

export async function fetchConfluencePages(limit = 20): Promise<ConfluencePage[]> {
  const response = await fetch(`${API_BASE_URL}/api/confluence/pages?limit=${limit}`);
  if (!response.ok) {
    throw new Error("Failed to fetch confluence pages");
  }
  const payload = (await response.json()) as { items?: ConfluencePage[] };
  return payload.items ?? [];
}

export async function syncConfluenceSources(force = true): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/confluence/sync?force=${force}`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error("Failed to sync confluence sources");
  }
}

export async function fetchAhaCategories(): Promise<string[]> {
  const response = await fetch(`${API_BASE_URL}/api/aha/categories`);
  if (!response.ok) throw new Error("Failed to fetch aha categories");
  const payload = (await response.json()) as { categories: string[] };
  return payload.categories ?? [];
}

export async function fetchAhaFeatures(
  limit = 200,
  offset = 0,
  category?: string,
): Promise<AhaFeaturePage> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (category && category !== "all") params.set("category", category);
  const response = await fetch(`${API_BASE_URL}/api/aha/ideas?${params}`);
  if (!response.ok) throw new Error("Failed to fetch aha ideas");
  return response.json() as Promise<AhaFeaturePage>;
}

export async function fetchCosmosContainers(): Promise<CosmosContainerInfo[]> {
  const response = await fetch(`${API_BASE_URL}/api/cosmos/containers`);
  if (!response.ok) {
    throw new Error("Failed to fetch Cosmos containers");
  }
  const payload = (await response.json()) as { items?: CosmosContainerInfo[] };
  return payload.items ?? [];
}

export async function runCosmosDiagnostics(
  payload: CosmosDiagnosticsRequest
): Promise<CosmosDiagnosticsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/cosmos/diagnostics/run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "Failed to run Cosmos diagnostics");
  }
  return response.json() as Promise<CosmosDiagnosticsResponse>;
}

export async function runCosmosAssistant(
  payload: CosmosAssistantRequest
): Promise<CosmosAssistantResponse> {
  const response = await fetch(`${API_BASE_URL}/api/cosmos/assistant`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "Failed to run Cosmos assistant");
  }
  return response.json() as Promise<CosmosAssistantResponse>;
}

export type ConsentFlowSection = {
  id: string;
  title: string;
  content: string;
  level: number;
  service: string;
  phase: string;
  excerpt: string;
};

export type ConsentFlowAskRequest = {
  question: string;
  section_id?: string | null;
};

export type ConsentFlowAskResponse = {
  answer: string;
  sections_used: Array<{ id: string; title: string }>;
  follow_up_questions: string[];
};

export async function fetchConsentFlowSections(): Promise<ConsentFlowSection[]> {
  const response = await fetch(`${API_BASE_URL}/api/consent-flow/sections`);
  if (!response.ok) {
    throw new Error("Failed to fetch consent flow sections");
  }
  const payload = (await response.json()) as { items?: ConsentFlowSection[] };
  return payload.items ?? [];
}

export async function askConsentFlow(
  payload: ConsentFlowAskRequest
): Promise<ConsentFlowAskResponse> {
  const response = await fetch(`${API_BASE_URL}/api/consent-flow/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "Failed to ask consent flow assistant");
  }
  return response.json() as Promise<ConsentFlowAskResponse>;
}

export async function indexConsentFlow(): Promise<{ indexed: number; total: number; message: string }> {
  const response = await fetch(`${API_BASE_URL}/api/consent-flow/index`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error("Failed to index consent flow");
  }
  return response.json() as Promise<{ indexed: number; total: number; message: string }>;
}
