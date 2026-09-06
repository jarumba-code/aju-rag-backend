import { NextRequest, NextResponse } from "next/server";

/**
 * Server-side origin of the FastAPI backend. Admin routes always pass full
 * paths (`/api/v1/...`), so any `/api/v1` suffix on the configured value is
 * stripped here to avoid requesting `/api/v1/api/v1/...`.
 *
 * `BACKEND_INTERNAL_URL` wins when set (container-to-container networking);
 * `NEXT_PUBLIC_API_URL` is the browser-facing fallback.
 */
const BACKEND = (
  process.env.BACKEND_INTERNAL_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000"
)
  .trim()
  .replace(/\/+$/, "")
  .replace(/\/api\/v1$/, "");
const COOKIE_NAME = "aju_admin_token";

/** Shared helper: proxy a request to FastAPI admin auth, set/clear cookie. */
export async function proxyToBackend(
  path: string,
  init: RequestInit = {}
): Promise<Response> {
  return fetch(`${BACKEND}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers as Record<string, string>),
    },
  });
}

export function getTokenFromCookies(req: NextRequest): string | null {
  return req.cookies.get(COOKIE_NAME)?.value ?? null;
}

export function buildAuthHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

export { COOKIE_NAME };
