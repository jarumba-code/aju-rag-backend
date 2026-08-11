import { NextRequest, NextResponse } from "next/server";
import { proxyToBackend, COOKIE_NAME } from "@/lib/adminProxy";

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));

  const backendRes = await proxyToBackend("/api/v1/admin/auth/login", {
    method: "POST",
    body: JSON.stringify({ password: body.password ?? "" }),
  }).catch(() => null);

  if (!backendRes) {
    return NextResponse.json({ detail: "Backend unreachable." }, { status: 502 });
  }

  if (!backendRes.ok) {
    const data = await backendRes.json().catch(() => ({}));
    return NextResponse.json(data, { status: backendRes.status });
  }

  const data = await backendRes.json();
  const token: string | undefined = data.access_token;

  if (!token) {
    return NextResponse.json({ detail: "No token received." }, { status: 500 });
  }

  const response = NextResponse.json({ role: data.role ?? "admin" }, { status: 200 });

  // Store the JWT exclusively in an HttpOnly, Secure, SameSite cookie.
  // Client-side JS cannot access this value.
  response.cookies.set(COOKIE_NAME, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict",
    path: "/",
    maxAge: 60 * 60 * 4, // 4 hours — matches ACCESS_TOKEN_EXPIRE_MINUTES
  });

  return response;
}
