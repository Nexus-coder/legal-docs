import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const token = request.cookies.get("token")?.value;
  const { pathname } = request.nextUrl;

  // Paths that are accessible without authentication
  const isAuthPage = pathname.startsWith("/login") || pathname.startsWith("/signup");
  const isPublicFile = pathname.startsWith("/_next") || pathname.includes(".");

  if (isPublicFile) {
    return NextResponse.next();
  }

  if (!token && !isAuthPage) {
    // Redirect to login if no token and trying to access protected page
    const url = new URL("/login", request.url);
    return NextResponse.redirect(url);
  }

  if (token && isAuthPage) {
    // Redirect to dashboard if token exists and trying to access login/signup
    const url = new URL("/", request.url);
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
};
