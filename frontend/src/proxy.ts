import { NextResponse, type NextRequest } from "next/server";

import { getPublicSiteUrl } from "@/lib/env";

const protectedPrefixes = ["/dashboard", "/profile"];
const adminPrefix = "/admin";

function isProtectedPath(pathname: string): boolean {
  if (pathname.startsWith(adminPrefix)) return true;
  if (/^\/courses\/[^/]+\/lessons(\/|$)/.test(pathname)) return true;
  return protectedPrefixes.some((prefix) => pathname.startsWith(prefix));
}

// www and the apex domain both reach this service (Cloudflare is DNS-only),
// so the 301 to the canonical host happens here. Only the exact www twin of
// NEXT_PUBLIC_SITE_URL is redirected, to a fixed origin: no open redirect.
function canonicalHostRedirect(request: NextRequest): NextResponse | undefined {
  const site = new URL(getPublicSiteUrl());
  const host = request.headers.get("host")?.toLowerCase();
  if (host !== `www.${site.host}`) return undefined;
  const target = new URL(`${request.nextUrl.pathname}${request.nextUrl.search}`, site.origin);
  return NextResponse.redirect(target, 301);
}

export function proxy(request: NextRequest) {
  const canonicalRedirect = canonicalHostRedirect(request);
  if (canonicalRedirect) return canonicalRedirect;

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
  // Every path, for the www redirect; build assets are only requested by
  // pages that were already served from the canonical host.
  matcher: ["/((?!_next/static|_next/image).*)"],
};
