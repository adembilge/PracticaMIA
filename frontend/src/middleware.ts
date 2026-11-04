import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';
import { auth0 } from '@/lib/auth0';

/** Next.js 15 middleware: Auth0 provides callback, login, logout and session routes. */
export async function middleware(request: NextRequest) {
  if (auth0) return auth0.middleware(request);
  if (request.nextUrl.pathname.startsWith('/auth/')) {
    return new NextResponse('Authentication has not been configured.', {
      status: 404,
      headers: { 'Cache-Control': 'no-store' },
    });
  }
  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)'],
};
