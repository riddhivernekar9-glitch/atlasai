/**
 * api.ts — typed wrappers around the AtlasAI FastAPI backend.
 *
 * The backend always runs locally on port 8000 (Tauri sidecar or direct
 * `uvicorn` process). All functions throw on network errors; callers are
 * responsible for try/catch.
 */

const BASE_URL = 'http://127.0.0.1:8000'

// ---------------------------------------------------------------------------
// Shared types (mirror server/app.py models)
// ---------------------------------------------------------------------------

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface SearchResult {
  relative_path: string
  path: string
  context: string
  score: number
  doc_type: string
}

export interface AnswerResponse {
  answer: string
  sources: SearchResult[]
  structured: Record<string, string>
  confidence: Record<string, string>
}

export interface IngestResponse {
  ok: boolean
  /** Number of files indexed */
  count?: number
  /** Total chunks stored */
  chunks?: number
  /** Absolute paths of indexed files */
  files?: string[]
  /** Human-readable error message when ok === false */
  error?: string
  /** Resolved folder path */
  folder?: string
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

/** Returns true when the backend is reachable and healthy. */
export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE_URL}/health`, { cache: 'no-store' })
    if (!res.ok) return false
    const data = await res.json()
    return data.status === 'ok'
  } catch {
    return false
  }
}

/**
 * Ingest all supported files under `path` into the vector index.
 *
 * @param path  Absolute path to a folder (or single file) on the local system.
 */
export async function ingestPath(path: string): Promise<IngestResponse> {
  const res = await fetch(`${BASE_URL}/api/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
    cache: 'no-store',
  })
  if (!res.ok) {
    throw new Error(`Ingest failed: HTTP ${res.status}`)
  }
  return res.json()
}

/**
 * Send a query to the answer endpoint, optionally including prior chat turns
 * so the model can handle follow-up questions.
 *
 * @param query    The user's latest question.
 * @param messages Prior conversation turns (oldest first).
 * @param limit    Max number of chunks to retrieve (default 3).
 */
export async function answerQuery(
  query: string,
  messages: ChatMessage[] = [],
  limit = 3,
): Promise<AnswerResponse> {
  const res = await fetch(`${BASE_URL}/api/answer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, messages, limit }),
    cache: 'no-store',
  })
  if (!res.ok) {
    throw new Error(`Answer request failed: HTTP ${res.status}`)
  }
  return res.json()
}
