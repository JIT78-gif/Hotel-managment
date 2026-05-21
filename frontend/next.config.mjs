/** @type {import('next').NextConfig} */
const BACKEND_PORT = process.env.BACKEND_PORT || "8000";
// BACKEND_URL overrides PORT (used in Docker / EasyPanel where backend lives on a different host)
const BACKEND_URL = process.env.BACKEND_URL || `http://localhost:${BACKEND_PORT}`;

const nextConfig = {
  reactStrictMode: true,
  // Standalone output produces a small self-contained server.js for Docker images
  output: "standalone",
  env: { NEXT_PUBLIC_BACKEND_PORT: BACKEND_PORT },
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "images.unsplash.com" }
    ]
  },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${BACKEND_URL}/:path*` }
    ];
  }
};

export default nextConfig;
