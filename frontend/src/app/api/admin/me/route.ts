import { NextRequest, NextResponse } from "next/server";
import { getTokenFromCookies, proxyToBackend, buildAuthHeaders } from "@/lib/adminProxy";

export async function GET(req: NextRequest) {
  const token = getTokenFromCookies(req);

  if (!token) {
    return NextResponse.json({ authenticated: false }, { status: 401 });
  }

  // Always validate the token against the backend — cookie presence is NOT sufficient.
  const backendRes = await proxyToBackend("/api/v1/admin/auth/me", {
    method: "GET",
    headers: buildAuthHeaders(token),
  }).catch(() => null);

  if (!backendRes || !backendRes.ok) {
    return NextResponse.json({ authenticated: false }, { status: 401 });
  }

  const data = await backendRes.json();
  return NextResponse.json({ authenticated: true, role: data.role ?? "admin" }, { status: 200 });
}
