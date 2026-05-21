import { NextResponse, type NextRequest } from "next/server";

// Reads the hc_staff cookie (JSON.stringified LoginResponse) and gates /staff/* and /admin/*.
// Customer routes (/, /c/*, /customer/*, /login) are open.
export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (!pathname.startsWith("/staff") && !pathname.startsWith("/admin")) {
    return NextResponse.next();
  }

  const raw = req.cookies.get("hc_staff")?.value;
  let role: string | undefined;
  if (raw) {
    try { role = JSON.parse(decodeURIComponent(raw))?.role; } catch {}
  }

  if (!role) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  if (pathname.startsWith("/admin") && role !== "admin") {
    const url = req.nextUrl.clone();
    url.pathname = "/staff/orders";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/staff/:path*", "/admin/:path*"],
};
