import { NextResponse } from "next/server";

/**
 * Extract id_token from appSession httpOnly cookie.
 * Properly handles URI-encoded cookie values and values containing "=" signs.
 * @param {Request} request - Next.js request object
 * @returns {{Authorization: string, "Content-Type": string} | null} - Headers object with Bearer token, or null if not found
 */
export function getBackendAuthHeaders(request) {
  try {
    const cookieHeader = request.headers.get("cookie") || "";

    if (!cookieHeader) {
      console.warn("[backendAuth] No cookie header present");
      return null;
    }

    // Split cookies properly - handles values with = signs inside
    const cookies = {};
    cookieHeader.split(";").forEach((part) => {
      const idx = part.indexOf("=");
      if (idx === -1) return;
      const key = part.slice(0, idx).trim();
      const val = part.slice(idx + 1).trim();
      cookies[key] = val;
    });

    const rawSession = cookies["appSession"];
    if (!rawSession) {
      console.warn("[backendAuth] appSession cookie not found");
      console.warn("[backendAuth] Available cookies:", Object.keys(cookies));
      return null;
    }

    // Decode URI encoding if present
    let sessionStr = rawSession;
    try {
      sessionStr = decodeURIComponent(rawSession);
    } catch {
      // Not URI encoded, use as-is
    }

    // Parse JSON session
    let sessionData;
    try {
      sessionData = JSON.parse(sessionStr);
    } catch (e) {
      console.warn("[backendAuth] Failed to parse appSession JSON:", e.message);
      console.warn(
        "[backendAuth] Raw session (first 100 chars):",
        sessionStr.slice(0, 100),
      );
      return null;
    }

    // Prefer id_token (standard JWT), fallback to access_token
    const token = sessionData.id_token || sessionData.access_token;
    if (!token) {
      console.warn(
        "[backendAuth] No token found in session. Keys:",
        Object.keys(sessionData),
      );
      return null;
    }

    console.log(
      "[backendAuth] Token extracted successfully, type:",
      sessionData.id_token ? "id_token" : "access_token",
    );

    return {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
  } catch (err) {
    console.error("[backendAuth] Unexpected error:", err.message);
    return null;
  }
}

/**
 * Forward any HTTP method (GET, POST, DELETE, PUT) to backend.
 * Auth headers are attached server-side from appSession cookie.
 * Body is only forwarded for methods that can have a body.
 */
export async function forwardToBackend(request, backendUrl, options = {}) {
  const authHeaders = await getBackendAuthHeaders(request);

  if (!authHeaders) {
    console.error(
      "[forwardToBackend] Auth extraction failed for:",
      request.method,
      backendUrl,
    );
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  const method = options.method || request.method;

  // Only read body for methods that support it
  const hasBody = ["POST", "PUT", "PATCH"].includes(method.toUpperCase());

  let body = undefined;
  if (hasBody) {
    try {
      body = await request.text();
    } catch {
      body = undefined;
    }
  }

  // Merge headers: original request content-type + auth headers
  const headers = {
    "Content-Type": "application/json",
    ...authHeaders,
    ...options.headers,
  };

  try {
    const fetchOptions = {
      method,
      headers,
      ...(body !== undefined && { body }),
    };

    console.log(`[forwardToBackend] ${method} ${backendUrl}`);

    // Debug logging for DELETE requests to trace 401 issues
    if (method.toUpperCase() === "DELETE") {
      const authHeader = headers["Authorization"] || headers.authorization;
      console.log("[forwardToBackend] DELETE debug:", {
        backendUrl,
        hasAuth: !!authHeader,
        contentType: headers["Content-Type"],
        method,
      });
    }

    const response = await fetch(backendUrl, fetchOptions);
    console.log(`[forwardToBackend] Response: ${response.status}`);

    // Return response as-is (pass through status + body)
    const responseBody = await response.text();
    return new NextResponse(responseBody, {
      status: response.status,
      headers: {
        "Content-Type":
          response.headers.get("Content-Type") || "application/json",
      },
    });
  } catch (err) {
    console.error("[forwardToBackend] Fetch error:", err.message);
    return NextResponse.json(
      { error: "Backend unreachable", detail: err.message },
      { status: 502 },
    );
  }
}
