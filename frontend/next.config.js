/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      // Catch-all rule that proxies ALL /api/backend/* calls to the backend
      // This covers portfolio, analytics, ai, market, and all other API routes
      {
        source: "/api/backend/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`,
      },
      // Per-asset market data routes (also support direct /api/mutual, /api/stock, /api/crypto)
      {
        source: "/api/mutual/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL}/api/mutual/:path*`,
      },
      {
        source: "/api/stock/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL}/api/stock/:path*`,
      },
      {
        source: "/api/crypto/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL}/api/crypto/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
