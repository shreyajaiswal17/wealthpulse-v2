import { forwardToBackend } from "@/app/lib/backendAuth";

/**
 * DELETE /api/backend/portfolio/[id] - Delete a holding by ID (forwarded to backend /api/portfolio/:id)
 */
export async function DELETE(request, { params }) {
  const { id } = await params;
  const backendUrl = `${process.env.NEXT_PUBLIC_API_URL}/api/portfolio/${id}`;
  const response = await forwardToBackend(request, backendUrl);
  return response;
}
