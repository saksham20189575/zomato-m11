import type { NextConfig } from "next";

// Node resolves "localhost" to ::1 first. Uvicorn's default bind is
// 127.0.0.1 only, so a localhost rewrite returns 502 (ECONNREFUSED on ::1).
const apiUrl = (
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000"
).replace("://localhost", "://127.0.0.1");

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/backend/:path*",
        destination: `${apiUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
