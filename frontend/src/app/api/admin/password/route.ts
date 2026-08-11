import { NextRequest, NextResponse } from "next/server";
import { getTokenFromCookies, proxyToBackend, buildAuthHeaders } from "@/lib/adminProxy";

export async function POST(req: NextRequest) {
  const token = getTokenFromCookies(req);

  if (!token) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  const body = await req.json().catch(() => ({}));

  const backendRes = await proxyToBackend("/api/v1/admin/auth/password", {
    method: "POST",
    headers: buildAuthHeaders(token),
    body: JSON.stringify({
      current_password: body.current_password ?? "",
      new_password: body.new_password ?? "",
    }),
  }).catch(() => null);

  if (!backendRes) {
    return NextResponse.json({ detail: "Backend unreachable." }, { status: 502 });
  }

  const data = await backendRes.json().catch(() => ({}));

  if (!backendRes.ok) {
    return NextResponse.json(data, { status: backendRes.status });
  }

  return NextResponse.json(data, { status: 200 });
}
