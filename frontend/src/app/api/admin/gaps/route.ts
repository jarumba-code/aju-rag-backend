import { NextRequest, NextResponse } from "next/server";
import { getTokenFromCookies, proxyToBackend, buildAuthHeaders } from "@/lib/adminProxy";

export async function GET(req: NextRequest) {
  const token = getTokenFromCookies(req);
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }
  const url = new URL(req.url);
  const qs = new URLSearchParams(url.search);
  const backendRes = await proxyToBackend(
    `/api/v1/analytics/gaps?${qs.toString()}`,
    {
      method: "GET",
      headers: buildAuthHeaders(token),
    }
  ).catch(() => null);

  if (!backendRes || !backendRes.ok) {
    return NextResponse.json({ detail: "Failed to fetch gaps." }, { status: backendRes?.status ?? 502 });
  }

  const data = await backendRes.json();
  return NextResponse.json(data, { status: 200 });
}
