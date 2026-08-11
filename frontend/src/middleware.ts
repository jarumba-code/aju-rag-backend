import { NextRequest, NextResponse } from "next/server";
import { getTokenFromCookies } from "@/lib/adminProxy";

export const config = {
  matcher: ["/admin/:path*"],
};

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // Allow the login page through unconditionally
  if (pathname === "/admin/login") return NextResponse.next();

  const token = getTokenFromCookies(req);

  // If no cookie present, redirect to login.
  // NOTE: this is UX-only. FastAPI validates the JWT on every actual API call.
  if (!token) {
    const loginUrl = req.nextUrl.clone();
    loginUrl.pathname = "/admin/login";
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}
