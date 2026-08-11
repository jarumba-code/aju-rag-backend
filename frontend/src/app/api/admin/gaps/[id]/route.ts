import { NextRequest, NextResponse } from "next/server";
import { getTokenFromCookies, proxyToBackend, buildAuthHeaders } from "@/lib/adminProxy";

export async function PATCH(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const token = getTokenFromCookies(req);
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  const body = await req.json().catch(() => ({}));
  const backendRes = await proxyToBackend(
    `/api/v1/analytics/gaps/${encodeURIComponent(params.id)}`,
    {
      method: "PATCH",
      headers: {
        ...buildAuthHeaders(token),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    }
  ).catch(() => null);

  if (!backendRes || !backendRes.ok) {
    let detail = "Failed to update gap.";
    try {
      const err = await backendRes?.json();
      if (err?.detail) detail = err.detail;
    } catch {}
    return NextResponse.json({ detail }, { status: backendRes?.status ?? 502 });
  }

  const data = await backendRes.json();
  return NextResponse.json(data, { status: 200 });
}
