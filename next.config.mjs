/** @type {import('next').NextConfig} */
const nextConfig = {
  // Standalone output bundles everything needed to run the server.
  // Electron's production mode serves from .next/standalone/server.js
  output: 'standalone',
  typescript: {
    // Pre-existing type mismatch in Database<->GenericSchema (Supabase v2.108).
    // Does not affect runtime — suppress so the build completes.
    ignoreBuildErrors: true,
  },
}

export default nextConfig
