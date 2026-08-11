import { NextRequest, NextResponse } from "next/server";
import { getTokenFromCookies, proxyToBackend, buildAuthHeaders } from "@/lib/adminProxy";

export async function DELETE(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const token = getTokenFromCookies(req);
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }
  const backendRes = await proxyToBackend(
    "/api/v1/admin/documents/" + encodeURIComponent(params.id),
    {
      method: "DELETE",
      headers: buildAuthHeaders(token),
    }
  ).catch(() => null);

  if (!backendRes || !backendRes.ok) {
    let detail = "Failed to delete document.";
    try {
      const body = await backendRes?.json();
      if (body?.detail) detail = body.detail;
    } catch {}
    return NextResponse.json({ detail }, { status: backendRes?.status ?? 502 });
  }

  const data = await backendRes.json();
  return NextResponse.json(data, { status: 200 });
}
