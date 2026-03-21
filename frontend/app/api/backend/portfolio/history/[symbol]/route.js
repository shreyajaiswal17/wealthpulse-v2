import { forwardToBackend } from "@/app/lib/backendAuth";

/**
 * GET /api/backend/portfolio/history/[symbol] - Get buy history for a specific symbol
 * Forwards to backend: GET /api/portfolio/history/{symbol}
 */
export async function GET(request, { params }) {
  const { symbol } = params;
  const backendUrl = `${process.env.NEXT_PUBLIC_API_URL}/api/portfolio/history/${encodeURIComponent(symbol)}`;
  console.log(
    "GET portfolio history for symbol:",
    symbol,
    "from backend:",
    backendUrl,
  );
  const response = await forwardToBackend(request, backendUrl);
  return response;
}
