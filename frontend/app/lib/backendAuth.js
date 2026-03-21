/**
 * Extract Auth0 token from appSession cookie and return headers with Authorization
 * @param {Request} request - Next.js request object
 * @returns {{Authorization: string} | null} - Headers object with Bearer token, or null if not found
 */
export function getBackendAuthHeaders(request) {
  try {
    const cookieHeader = request.headers.get("cookie");
    if (!cookieHeader) {
      console.warn("No cookie header found");
      return null;
    }

    // Parse appSession cookie
    const cookies = cookieHeader.split(";").reduce((acc, cookie) => {
      const [name, value] = cookie.trim().split("=");
      acc[name] = value;
      return acc;
    }, {});

    const appSessionCookie = cookies.appSession;
    if (!appSessionCookie) {
      console.warn("No appSession cookie found");
      return null;
    }

    // Decode the cookie (it's URL-encoded JSON)
    const sessionData = JSON.parse(decodeURIComponent(appSessionCookie));

    // Use id_token (regular JWT) instead of access_token (JWE encrypted)
    // Backend can decode id_token without decryption
    const token = sessionData.id_token || sessionData.access_token;
    if (!token) {
      console.warn("No id_token or access_token in appSession");
      return null;
    }

    return {
      Authorization: `Bearer ${token}`,
    };
  } catch (error) {
    console.error("Error extracting backend auth headers:", error);
    return null;
  }
}

/**
 * Forward a request to the backend with authentication
 * @param {Request} request - Next.js request object
 * @param {string} backendUrl - Full URL to backend endpoint
 * @param {object} options - Additional fetch options (method, headers, body)
 * @returns {Promise<Response>} - Backend response
 */
export async function forwardToBackend(request, backendUrl, options = {}) {
  const authHeaders = getBackendAuthHeaders(request);

  if (!authHeaders) {
    return new Response(
      JSON.stringify({ error: "Unauthorized: No valid auth token" }),
      { status: 401, headers: { "Content-Type": "application/json" } },
    );
  }

  const fetchOptions = {
    method: request.method,
    headers: {
      ...authHeaders,
      ...(options.headers || {}),
    },
    ...options,
  };

  // For GET requests, don't include body
  if (request.method === "GET") {
    delete fetchOptions.body;
  } else if (!fetchOptions.body && request.body) {
    // For POST/PUT/PATCH, forward the request body
    fetchOptions.body = await request.text();
  }

  try {
    const response = await fetch(backendUrl, fetchOptions);
    return response;
  } catch (error) {
    console.error("Error forwarding to backend:", error);
    return new Response(JSON.stringify({ error: "Backend request failed" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
}
