// next.config.js
module.exports = {
  async rewrites() {
    return [
      // Per-asset market data (mutual funds, stocks, crypto)
      {
        source: "/api/mutual/:path*",
        destination: "http://localhost:8000/api/mutual/:path*", // your FastAPI mutual funds route
      },
      {
        source: "/api/stock/:path*",
        destination: "http://localhost:8000/api/stock/:path*", // your FastAPI stock route
      },
      {
        source: "/api/crypto/:path*",
        destination: "http://localhost:8000/api/crypto/:path*", // your FastAPI crypto route
      },
      // WealthPulse v2 backend proxies (with auth headers added by /api/backend/* routes)
      {
        source: "/api/backend/portfolio",
        destination: "http://localhost:8000/api/portfolio",
      },
      {
        source: "/api/backend/portfolio/:id",
        destination: "http://localhost:8000/api/portfolio/:id",
      },
      {
        source: "/api/backend/analytics/portfolio",
        destination: "http://localhost:8000/api/analytics/portfolio",
      },
      {
        source: "/api/backend/ai/dost",
        destination: "http://localhost:8000/api/ai/dost",
      },
      {
        source: "/api/backend/ai/report",
        destination: "http://localhost:8000/api/ai/report",
      },
      {
        source: "/api/backend/market/:path*",
        destination: "http://localhost:8000/api/market/:path*",
      },
    ];
  },
};
