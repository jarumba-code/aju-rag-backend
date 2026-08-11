import { NextRequest, NextResponse } from "next/server";
import { getTokenFromCookies, proxyToBackend, buildAuthHeaders, COOKIE_NAME } from "@/lib/adminProxy";

export async function POST(req: NextRequest) {
  const token = getTokenFromCookies(req);

  if (token) {
    // Best-effort: notify backend so it can record the logout event.
    await proxyToBackend("/api/v1/admin/auth/logout", {
      method: "POST",
      headers: buildAuthHeaders(token),
    }).catch(() => {});
  }

  const response = NextResponse.json({ authenticated: false }, { status: 200 });
  response.cookies.set(COOKIE_NAME, "", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict",
    path: "/",
    maxAge: 0, // Expire immediately
  });
  return response;
}
