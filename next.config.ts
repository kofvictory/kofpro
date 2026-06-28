import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  // Standalone output bundles everything needed to run the server.
  // Electron's production mode serves from .next/standalone/server.js
  output: 'standalone',
}

export default nextConfig
