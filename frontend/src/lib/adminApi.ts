/**
 * Admin API client for the AJU Admin Portal.
 *
 * All admin requests go through Next.js API route proxies so the JWT token
 * is stored exclusively in HttpOnly cookies and never visible to client-side JS.
 */

export interface AdminLoginPayload {
  password: string;
}

export interface AdminMeResponse {
  authenticated: boolean;
  role?: string;
}

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
}

export interface DocumentRecord {
  id: string;
  filename: string;
  file_hash: string;
  department: string | null;
  doc_type: string | null;
  chunk_count: number;
  created_at: string;
}

export interface AnalyticsSummary {
  total_documents: number;
  total_chunks: number;
  total_answered: number;
  total_unanswered: number;
  avg_confidence: number;
  avg_latency_ms: number;
  resolution_rate: number;
}

export interface AnalyticsTrends {
  query_volume: {
    labels: string[];
    data: number[];
  };
  source_utilization: Array<{
    document_id: string;
    chunk_count: number;
  }>;
}

export interface GapRecord {
  id: string;
  query_text: string;
  normalized_query: string;
  reason: string;
  confidence_score: number | null;
  retrieved_documents: number;
  conversation_id: string | null;
  user_id: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string | null;
  resolved: boolean;
  resolution_note: string | null;
}

export interface TopGapRecord {
  representative_query: string;
  frequency: number;
  last_seen: string | null;
}

export interface AuditLogRecord {
  id: number;
  timestamp: string;
  user_role: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  details: string | null;
  status: string;
  ip_address: string | null;
}

export class AdminApiError extends Error {
  readonly status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "AdminApiError";
    this.status = status;
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {}
    throw new AdminApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

export async function adminLogin(password: string): Promise<{ role: string }> {
  const res = await fetch("/api/admin/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
    credentials: "same-origin",
  });
  return handleResponse<{ role: string }>(res);
}

export async function adminLogout(): Promise<void> {
  await fetch("/api/admin/logout", { method: "POST", credentials: "same-origin" });
}

export async function adminMe(): Promise<AdminMeResponse> {
  const res = await fetch("/api/admin/me", { credentials: "same-origin" });
  return handleResponse<AdminMeResponse>(res);
}

export async function changeAdminPassword(
  current_password: string,
  new_password: string
): Promise<{ message: string }> {
  const res = await fetch("/api/admin/password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ current_password, new_password }),
    credentials: "same-origin",
  });
  return handleResponse<{ message: string }>(res);
}

export async function adminDocuments(): Promise<DocumentRecord[]> {
  const res = await fetch("/api/admin/documents", { credentials: "same-origin" });
  return handleResponse<DocumentRecord[]>(res);
}

export async function adminUploadDocument(
  file: File,
  department?: string,
  docType?: string
): Promise<{ status: string; document_id: string; filename: string; department?: string; doc_type?: string }> {
  const formData = new FormData();
  formData.append("file", file);
  if (department) formData.append("department", department);
  if (docType) formData.append("doc_type", docType);

  const res = await fetch("/api/admin/documents/upload", {
    method: "POST",
    body: formData,
    credentials: "same-origin",
  });
  return handleResponse(res);
}

export async function adminDeleteDocument(documentId: string): Promise<{ status: string; document_id: string }> {
  const res = await fetch(`/api/admin/documents/${encodeURIComponent(documentId)}`, {
    method: "DELETE",
    credentials: "same-origin",
  });
  return handleResponse(res);
}

export async function adminAnalyticsSummary(): Promise<AnalyticsSummary> {
  const res = await fetch("/api/admin/analytics/summary", { credentials: "same-origin" });
  return handleResponse<AnalyticsSummary>(res);
}

export async function adminAnalyticsTrends(days = 7): Promise<AnalyticsTrends> {
  const res = await fetch(`/api/admin/analytics/trends?days=${days}`, { credentials: "same-origin" });
  return handleResponse<AnalyticsTrends>(res);
}

export async function adminAuditLog(params?: {
  limit?: number;
  offset?: number;
  action?: string;
  status?: string;
}): Promise<{ logs: AuditLogRecord[]; total: number }> {
  const qs = new URLSearchParams();
  if (params?.limit) qs.set("limit", String(params.limit));
  if (params?.offset) qs.set("offset", String(params.offset));
  if (params?.action) qs.set("action", params.action);
  if (params?.status) qs.set("status", params.status);

  const res = await fetch(`/api/admin/audit-log?${qs.toString()}`, { credentials: "same-origin" });
  return handleResponse(res);
}

export async function adminGaps(params?: {
  limit?: number;
  offset?: number;
  reason?: string;
  resolved?: boolean;
}): Promise<{ total_gaps: number; recent_gaps: GapRecord[]; grouped_by_reason: Record<string, number> }> {
  const qs = new URLSearchParams();
  if (params?.limit) qs.set("limit", String(params.limit));
  if (params?.offset) qs.set("offset", String(params.offset));
  if (params?.reason) qs.set("reason", params.reason);
  if (params?.resolved !== undefined) qs.set("resolved", String(params.resolved));

  const res = await fetch(`/api/admin/gaps?${qs.toString()}`, { credentials: "same-origin" });
  return handleResponse(res);
}

export async function adminUpdateGap(
  gapId: string,
  payload: { resolved?: boolean; resolution_note?: string }
): Promise<{ id: string; resolved: boolean; resolution_note: string | null }> {
  const res = await fetch(`/api/admin/gaps/${encodeURIComponent(gapId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    credentials: "same-origin",
  });
  return handleResponse(res);
}

export async function adminTopGaps(limit = 20): Promise<TopGapRecord[]> {
  const res = await fetch(`/api/admin/gaps/top?limit=${limit}`, { credentials: "same-origin" });
  return handleResponse<TopGapRecord[]>(res);
}

export async function adminSuggestedQuestions(limit = 10): Promise<string[]> {
  const res = await fetch(`/api/admin/suggested-questions?limit=${limit}`);
  return handleResponse<string[]>(res);
}
