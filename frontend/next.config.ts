import type { NextConfig } from "next";

// Where /api requests are forwarded when the frontend and backend share one server (the Docker image).
// Rewrites are fixed at build time, so this is read by `next build`, not at startup.
const apiProxyTarget = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // The Docker image runs a self-contained server; local `next start` keeps the usual output.
  output: process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined,
  experimental: {
    // An analysis can go quiet for over a minute while Claude drafts; the default proxy timeout is 30 s.
    proxyTimeout: 10 * 60 * 1000,
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiProxyTarget}/api/:path*` }];
  },
};

export default nextConfig;
