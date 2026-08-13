import { NextRequest, NextResponse } from "next/server";
import { proxyToBackend } from "@/lib/adminProxy";

export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const limit = url.searchParams.get("limit") || "10";
  const backendRes = await proxyToBackend(
    `/api/v1/suggested?limit=${encodeURIComponent(limit)}`,
    {}
  ).catch(() => null);

  if (!backendRes || !backendRes.ok) {
    return NextResponse.json({ detail: "Failed to fetch suggested questions." }, { status: backendRes?.status ?? 502 });
  }

  const data = await backendRes.json();
  return NextResponse.json(data, { status: 200 });
}
