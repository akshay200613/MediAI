import type { NextConfig } from 'next'
import { loadEnvConfig } from '@next/env'
import path from "path"

loadEnvConfig(path.resolve(process.cwd(), '../..'))

const nextConfig: NextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true, // Only if type-check is run separately
  },
  experimental: {
    optimizePackageImports: ['lucide-react', 'date-fns', 'framer-motion'],
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/:path*`,
      },
    ]
  },
}

export default nextConfig
