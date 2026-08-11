import { NextRequest, NextResponse } from "next/server";
import { getTokenFromCookies, proxyToBackend, buildAuthHeaders } from "@/lib/adminProxy";

export async function POST(req: NextRequest) {
  const token = getTokenFromCookies(req);
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  const formData = await req.formData();
  const backendRes = await fetch(
    process.env.NEXT_PUBLIC_API_URL + "/api/v1/admin/documents/upload",
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    }
  ).catch(() => null);

  if (!backendRes || !backendRes.ok) {
    let detail = "Failed to upload document.";
    try {
      const body = await backendRes?.json();
      if (body?.detail) detail = body.detail;
    } catch {}
    return NextResponse.json({ detail }, { status: backendRes?.status ?? 502 });
  }

  const data = await backendRes.json();
  return NextResponse.json(data, { status: 200 });
}
