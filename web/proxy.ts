import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

/**
 * Runs on every request (except static assets).
 *
 * Responsibilities:
 *   1. Refresh the Supabase session cookie so it never silently expires.
 *   2. Redirect unauthenticated visitors away from /dashboard → /login.
 *   3. Redirect authenticated visitors away from /login → /dashboard.
 *   4. Redirect / → /dashboard (authenticated) or /login (not authenticated).
 */
export async function proxy(request: NextRequest) {
  let response = NextResponse.next({ request })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          // Propagate new cookies onto the request then onto the response
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value),
          )
          response = NextResponse.next({ request })
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options),
          )
        },
      },
    },
  )

  // Refresh session (also validates JWT; do NOT use getSession() here)
  const {
    data: { user },
  } = await supabase.auth.getUser()

  const { pathname } = request.nextUrl

  // Root → smart redirect
  if (pathname === '/') {
    const url = request.nextUrl.clone()
    url.pathname = user ? '/dashboard' : '/login'
    return NextResponse.redirect(url)
  }

  // Guard /dashboard for authenticated users only
  if (pathname.startsWith('/dashboard') && !user) {
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    return NextResponse.redirect(url)
  }

  // Already logged in — skip the login page
  if (pathname === '/login' && user) {
    const url = request.nextUrl.clone()
    url.pathname = '/dashboard'
    return NextResponse.redirect(url)
  }

  return response
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     *   - _next/static  (static files)
     *   - _next/image   (image optimisation)
     *   - favicon.ico
     *   - public folder files
     */
    '/((?!_next/static|_next/image|favicon\\.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}
