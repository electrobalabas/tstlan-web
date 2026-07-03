import type { NextConfig } from "next";

const backendOrigin = process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${backendOrigin}/:path*` },
      { source: "/docs", destination: `${backendOrigin}/docs` },
      { source: "/docs/:path*", destination: `${backendOrigin}/docs/:path*` },
      { source: "/openapi.json", destination: `${backendOrigin}/openapi.json` },
    ];
  },
};

export default nextConfig;
