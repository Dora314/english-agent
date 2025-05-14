// frontend/src/middleware.ts
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { getToken } from "next-auth/jwt"; // Helper to get JWT token

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // Allow requests for NextAuth API routes (e.g., /api/auth/*)
  // Allow requests for static files (_next/*, favicon.ico)
  if (
    pathname.startsWith("/api/auth") ||
    pathname.startsWith("/_next") ||
    pathname.startsWith("/static") || // if you have a /public/static folder
    pathname.endsWith(".ico") || // for favicon
    pathname.endsWith(".png") || // for images, etc.
    pathname.endsWith(".jpg") ||
    pathname.endsWith(".svg")
    // pathname === '/' // Allow access to the root page (our login page)
  ) {
    return NextResponse.next();
  }

  // Only allow access to the root page if not authenticated
  if (pathname === "/") {
    const tokenForRootAccess = await getToken({
      req,
      secret: process.env.NEXTAUTH_SECRET,
    });
    if (tokenForRootAccess) {
      // If authenticated and on root page
      console.log(
        "Middleware: Authenticated user on root page, redirecting to /home"
      );
      return NextResponse.redirect(new URL("/home", req.url));
    }
    // If not authenticated and on root page, allow access (it's the login page)
    console.log(
      "Middleware: Unauthenticated user on root page, allowing access."
    );
    return NextResponse.next();
  }

  // Get the token.
  // Note: `getToken` requires the raw `req` object, not the NextRequest enhanced one
  // if you are in an Edge environment. For Node.js runtime (default), `req` is fine.
  // The secret must match the one used in `authOptions`.
  const token = await getToken({ req, secret: process.env.NEXTAUTH_SECRET });

  // If no token (user not authenticated) and trying to access a protected route
  if (!token) {
    // Redirect to the login page (root in our case)
    // Preserve the original path as a callbackUrl so user is redirected back after login
    const loginUrl = new URL("/", req.url);
    loginUrl.searchParams.set("callbackUrl", pathname); // Or req.nextUrl.pathname
    return NextResponse.redirect(loginUrl);
  }

  // If authenticated and trying to access the root/login page, redirect to /home
  if (token && pathname === "/") {
    return NextResponse.redirect(new URL("/home", req.url));
  }

  // If token exists and not accessing the login page, allow the request
  return NextResponse.next();
}

// See "Matching Paths" below to learn more
// This configures the middleware to run on all paths except for some specific ones.
// Adjust the matcher if necessary.
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes) - we handle /api/auth specifically above
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     *
     * Or you can be more explicit about protected routes.
     * For now, we protect everything not explicitly allowed above.
     */
    "/((?!_next/static|_next/image|favicon.ico|api/auth).*)", // More robust general matcher
    "/", // Explicitly include the root to handle redirecting logged-in users
  ],
};
