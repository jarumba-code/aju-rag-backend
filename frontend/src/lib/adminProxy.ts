import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
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
