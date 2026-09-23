// Thin wrapper around the backend's /query/ endpoint (see app/routers/query.py + app/models/schemas.py).
// Base URL comes from NEXT_PUBLIC_API_URL (see .env.local); no trailing slash expected.

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '')

export type SourceInfo = { source: string; source_type: string | null }
export type QueryResponse = { answer: string; sources: SourceInfo[]; session_id: string }

// FastAPI/pydantic error bodies come in one of two shapes:
//  - { detail: "some string" }                          — raised explicitly by our own route handlers
//  - { detail: [{ type, loc, msg, input }, ...] }        — pydantic request-validation failures
type ValidationError = { type: string; loc: (string | number)[]; msg: string }

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function errorMessageFor(response: Response): Promise<string> {
  let body: unknown
  try {
    body = await response.json()
  } catch {
    return `The server returned an unexpected error (${response.status}).`
  }
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = (detail as ValidationError[]).map((d) => d.msg).filter(Boolean)
    if (messages.length) return messages.join('; ')
  }
  return `The server returned an unexpected error (${response.status}).`
}

// Rejects with ApiError for both network failures (status 0) and non-2xx responses.
// `k` overrides the backend's default top-k retrieval count (schema allows 1–10); omit to let the
// backend use its own default. Pass `signal` so an in-flight request can be cancelled (e.g. the
// user starts a new chat).
export async function askQuestion(question: string, sessionId: string, options?: { k?: number; signal?: AbortSignal }): Promise<QueryResponse> {
  const { k, signal } = options ?? {}
  let response: Response
  try {
    response = await fetch(`${API_URL}/query/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, session_id: sessionId, ...(k ? { k } : {}) }),
      signal,
    })
  } catch (err) {
    // A signal-triggered abort also lands here; let the caller check signal.aborted to
    // distinguish "the user cancelled this" from "the network actually failed".
    if (signal?.aborted) throw err
    throw new ApiError('Could not reach the server. Check that the backend is running and reachable.', 0)
  }
  if (!response.ok) throw new ApiError(await errorMessageFor(response), response.status)
  return response.json() as Promise<QueryResponse>
}