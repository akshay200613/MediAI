import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  // Authentication & role authorization are enforced per-tab via sessionStorage
  // in client-side AuthProvider and DashboardLayout components.
  return NextResponse.next()
}

export const config = {
  matcher: ['/admin/:path*', '/doctor/:path*', '/patient/:path*'],
}
