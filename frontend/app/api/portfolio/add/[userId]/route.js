import { NextResponse } from "next/server";

export async function POST(request, { params }) {
  const { userId } = await params;

  try {
    const body = await request.json();
    console.log("Received request to add portfolio item:", { userId, body });

    // Check if NEXT_PUBLIC_API_URL is defined
    if (!process.env.NEXT_PUBLIC_API_URL) {
      console.error("NEXT_PUBLIC_API_URL is not defined");
      return NextResponse.json(
        { detail: "API URL configuration error" },
        { status: 500 },
      );
    }

    const apiUrl = `${process.env.NEXT_PUBLIC_API_URL}/api/portfolio/add/${userId}`;
    console.log("Calling FastAPI endpoint:", apiUrl);

    // Extract auth token from appSession cookie
    const cookieHeader = request.headers.get("cookie");
    let authHeaders = { "Content-Type": "application/json" };

    console.log("Cookie header present:", !!cookieHeader);
    if (cookieHeader) {
      console.log("Raw cookie header:", cookieHeader);
      try {
        const cookies = cookieHeader.split(";").reduce((acc, cookie) => {
          const [name, value] = cookie.trim().split("=");
          acc[name] = value;
          return acc;
        }, {});

        console.log("Parsed cookies:", Object.keys(cookies));
        const appSessionCookie = cookies.appSession;
        console.log("appSession cookie present:", !!appSessionCookie);

        if (appSessionCookie) {
          console.log(
            "appSession cookie value length:",
            appSessionCookie.length,
          );
          const sessionData = JSON.parse(decodeURIComponent(appSessionCookie));
          console.log("Session data keys:", Object.keys(sessionData));

          // Use id_token (regular JWT) instead of access_token (JWE encrypted)
          // Backend can decode id_token without decryption
          const token = sessionData.id_token || sessionData.access_token;
          console.log("Token present:", !!token);
          console.log(
            "Using token type:",
            sessionData.id_token ? "id_token" : "access_token",
          );

          if (token) {
            authHeaders["Authorization"] = `Bearer ${token}`;
            console.log("Authorization header set");
          }
        }
      } catch (error) {
        console.warn(
          "Could not extract auth token from cookie:",
          error.message,
        );
        console.error("Cookie parsing error details:", error);
      }
    } else {
      console.warn("No cookie header found in request");
    }

    const response = await fetch(apiUrl, {
      method: "POST",
      headers: authHeaders,
      body: JSON.stringify(body),
    });

    console.log("Request headers sent:", {
      hasAuthorization: !!authHeaders.Authorization,
      authorizationPrefix: authHeaders.Authorization
        ? authHeaders.Authorization.substring(0, 20)
        : "none",
    });

    const responseText = await response.text();
    console.log("FastAPI response:", response.status, responseText);

    let responseData;
    try {
      responseData = JSON.parse(responseText);
    } catch (e) {
      console.error("Error parsing response:", e);
      return NextResponse.json(
        { detail: "Invalid response from API" },
        { status: 500 },
      );
    }

    if (!response.ok) {
      return NextResponse.json(responseData, { status: response.status });
    }

    return NextResponse.json(responseData);
  } catch (error) {
    console.error("Error in portfolio add API route:", error);
    return NextResponse.json(
      { detail: error.message || "Internal server error" },
      { status: 500 },
    );
  }
}
