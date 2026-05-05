import { NextResponse, type NextRequest } from "next/server";

const protectedPrefixes = ["/dashboard", "/profile"];
const adminPrefix = "/admin";

function isProtectedPath(pathname: string): boolean {
  if (pathname.startsWith(adminPrefix)) return true;
  if (/^\/courses\/[^/]+\/lessons(\/|$)/.test(pathname)) return true;
  return protectedPrefixes.some((prefix) => pathname.startsWith(prefix));
}

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  if (!isProtectedPath(pathname)) {
    return NextResponse.next();
  }

  const hasSession = request.cookies.get("auth_session")?.value === "1";
  if (hasSession) {
    return NextResponse.next();
  }

  const loginUrl = new URL("/auth/login", request.url);
  loginUrl.searchParams.set("next", `${pathname}${search}`);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ["/dashboard/:path*", "/profile/:path*", "/courses/:path*", "/admin/:path*"],
};
