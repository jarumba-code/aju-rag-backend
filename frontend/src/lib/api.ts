/**
 * Central API client for the AJU Smart Portal frontend.
 *
 * All backend communication for the chat widget, ingestion, and suggestions is
 * routed through this module so React components never scatter `fetch()` calls.
 *
 * The backend base URL comes from `NEXT_PUBLIC_API_URL` (an *origin*, e.g.
 * `http://localhost:8000`). The `/api/v1` prefix is appended automatically when
 * the configured value does not already include it.
 */

export type Persona = "public" | "student" | "staff";

const RAW_API_URL: string =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const normalizeBaseUrl = (raw: string): string => {
  const trimmed = raw.trim().replace(/\/+$/, "");
  return trimmed.endsWith("/api/v1") ? trimmed : `${trimmed}/api/v1`;
};

export const API_BASE_URL: string = normalizeBaseUrl(RAW_API_URL);

// ---------------------------------------------------------------------------
// Types — mirror the backend Pydantic schemas (public contract only, no
// internal SQLAlchemy models are exposed to the frontend).
// ---------------------------------------------------------------------------

export interface QueryResult {
  answer: string;
  sources: string[];
  conversation_id: string;
  confidence_met: boolean;
  confidence_score?: number | null;
  telemetry?: Record<string, unknown>;
}

export interface QueryPayload {
  query: string;
  persona: Persona;
  conversation_id?: string | null;
}

export interface SseStart {
  query: string;
  persona: string;
}

export interface SseCitation {
  source_title: string;
  similarity_score?: number;
  chunk_id?: number;
}

export interface SseMetadata {
  retrieved_chunk_count?: number;
  avg_similarity_score?: number;
  retrieval_latency_ms?: number;
}

export interface SseDone {
  answer: string;
  conversation_id: string;
  confidence_score?: number | null;
  confidence_met?: boolean;
  sources: string[];
  telemetry?: Record<string, unknown>;
}

export interface SseError {
  detail?: string;
}

export interface StreamCallbacks {
  onStart?: (data: SseStart) => void;
  onCitation?: (citation: SseCitation) => void;
  onMetadata?: (meta: SseMetadata) => void;
  onToken?: (text: string) => void;
  onDone?: (done: SseDone) => void;
  onError?: (message: string) => void;
}

export interface IngestPayload {
  title: string;
  content: string;
  is_confidential: boolean;
  department_id?: number | null;
  category_id?: number | null;
}
// ---------------------------------------------------------------------------
// Error helpers
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  readonly status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const extractDetail = (data: unknown): string => {
  if (
    data &&
    typeof data === "object" &&
    "detail" in data &&
    typeof (data as { detail: unknown }).detail === "string"
  ) {
    return (data as { detail: string }).detail;
  }
  return "";
};

async function throwForResponse(response: Response): Promise<void> {
  let detail = "";
  try {
    detail = extractDetail(await response.json());
  } catch {
    // non-JSON error body — fall through to generic message
  }
  if (detail) {
    throw new ApiError(detail, response.status);
  }
  throw new ApiError(`Request failed with status ${response.status}.`, response.status);
}

// ---------------------------------------------------------------------------
// Requests
// ---------------------------------------------------------------------------

const DEFAULT_HEADERS: Record<string, string> = { "Content-Type": "application/json" };

/** Non-streaming RAG query (POST /api/v1/query). */
export async function queryDocumentation(payload: QueryPayload): Promise<QueryResult> {
  const response = await fetch(`${API_BASE_URL}/query`, {
    method: "POST",
    headers: DEFAULT_HEADERS,
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    await throwForResponse(response);
  }
  return (await response.json()) as QueryResult;
}

/**
 * Streaming RAG query (POST /api/v1/query/stream).
 *
 * Parses Server-Sent Events frames (`start`, `citation`, `metadata`, `token`,
 * `done`, `error`) as they arrive and invokes the matching callback. Token text
 * is delivered progressively so the UI can render while the LLM streams.
 *
 * @param controller optional AbortController — aborts the fetch and the stream.
 */
export async function streamChat(
  payload: QueryPayload,
  callbacks: StreamCallbacks,
  controller?: AbortController
): Promise<void> {
const response = await fetch(`${API_BASE_URL}/query/stream`, {
    method: "POST",
    headers: DEFAULT_HEADERS,
    body: JSON.stringify(payload),
    signal: controller?.signal,
  });

  if (!response.ok) {
    await throwForResponse(response);
  }
  if (!response.body) {
    throw new ApiError("The server did not return a stream.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  const dispatch = (event: string, data: unknown): void => {
    switch (event) {
      case "start":
        callbacks.onStart?.(data as SseStart);
        break;
      case "citation":
        callbacks.onCitation?.(data as SseCitation);
        break;
      case "metadata":
        callbacks.onMetadata?.(data as SseMetadata);
        break;
      case "token":
        callbacks.onToken?.((data as { text?: string }).text ?? "");
        break;
      case "done":
        callbacks.onDone?.(data as SseDone);
        break;
      case "error": {
        const message =
          extractDetail(data) || "The assistant encountered an error. Please try again.";
        callbacks.onError?.(message);
        break;
      }
      default:
        break; // ignore unknown event types
    }
  };

  for (;;) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    // SSE frames are separated by a blank line; tolerate CRLF from any proxy.
    buffer = buffer.replace(/\r\n/g, "\n");
    let frameEnd = buffer.indexOf("\n\n");
    while (frameEnd !== -1) {
      const frame = buffer.slice(0, frameEnd);
      buffer = buffer.slice(frameEnd + 2);

      const lines = frame.split("\n");
      const eventLine = lines.find((l) => l.startsWith("event:"));
      const dataLines = lines
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).trim());

      if (eventLine && dataLines.length > 0) {
        const eventName = eventLine.slice(6).trim();
        const rawData = dataLines.join("\n");
        let parsed: unknown = rawData;
        try {
          parsed = JSON.parse(rawData);
        } catch {
          // not JSON — keep raw string
        }
        dispatch(eventName, parsed);
      }

      frameEnd = buffer.indexOf("\n\n");
    }
  }
}

/** Get suggested questions (GET /api/v1/suggested). */
export async function fetchSuggestedQuestions(limit = 5): Promise<string[]> {
  const response = await fetch(`${API_BASE_URL}/suggested?limit=${limit}`);
  if (!response.ok) {
    await throwForResponse(response);
  }
  const data = (await response.json()) as { questions?: string[] };
  return Array.isArray(data.questions) ? data.questions : [];
}

/**
 * Ingest institutional content (POST /api/v1/ingest).
 *
 * Admin-only on the backend — requires the admin API key, which the caller must
 * supply. The key is held in memory by the form and NEVER compiled into the
 * client bundle.
 */
export async function ingestDocument(
  payload: IngestPayload,
  adminApiKey: string
): Promise<{ message: string; source_id: number }> {
  const response = await fetch(`${API_BASE_URL}/ingest`, {
    method: "POST",
    headers: {
      ...DEFAULT_HEADERS,
      "X-API-Key": adminApiKey,
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    await throwForResponse(response);
  }
  return (await response.json()) as { message: string; source_id: number };
}