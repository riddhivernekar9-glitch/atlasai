export type SourceChunk = {
  relative_path: string;
  path: string;
  score: number;
  context: string;
  doc_type?: string;
};

export type AnswerResponse = {
  answer: string;
  sources: SourceChunk[];
  structured?: Record<string, string>;
  confidence?: Record<string, string>;
  raw?: any;
};

export type SearchResponse = {
  results: SourceChunk[];
};

export type IngestResponse = {
  ok: boolean;
  error?: string;
  folder?: string;
  count?: number;
  chunks?: number;
  files?: string[];
};

const BASE = "http://127.0.0.1:8000";

async function postJSON<T>(url: string, body: any): Promise<T> {
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `HTTP ${res.status}`);
    }

    return res.json();
  } catch (err: any) {
    if (err?.message?.includes("Failed to fetch")) {
      throw new Error(
        "Failed to fetch. The AtlasAI backend may not be running or reachable on this machine."
      );
    }
    throw err;
  }
}

export async function apiIngest(path: string): Promise<IngestResponse> {
  return postJSON<IngestResponse>(`${BASE}/api/ingest`, { path });
}

export async function apiAnswer(query: string, limit: number): Promise<AnswerResponse> {
  return postJSON<AnswerResponse>(`${BASE}/api/answer`, { query, limit });
}

export async function apiSearch(query: string, limit: number): Promise<SearchResponse> {
  return postJSON<SearchResponse>(`${BASE}/api/search`, { query, limit });
}