import { NextResponse } from "next/server";
import Groq from "groq-sdk";
import { GoogleGenerativeAI } from "@google/generative-ai";

// Initialize clients
const groqClient = new Groq({ apiKey: process.env.GROQ_API_KEY });
const geminiClient = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

// Helper: Create Groq stream
async function createGroqStream(messages, options = {}) {
  const completion = await groqClient.chat.completions.create({
    model: "llama-3.3-70b-versatile",
    messages,
    stream: true,
    temperature: options.temperature ?? 0.7,
    max_tokens: options.max_tokens ?? 1024,
  });
  return completion;
}

// Helper: Create Gemini stream (format-normalized output)
async function createGeminiStream(messages, options = {}) {
  const model = geminiClient.getGenerativeModel({
    model: "gemini-2.0-flash",
  });

  // Convert OpenAI-style messages to Gemini format
  // Note: Gemini doesn't support system role; prepend system as first user message
  let contents = messages.map(m => ({
    role: m.role === "system" ? "user" : (m.role === "assistant" ? "model" : "user"),
    parts: [{ text: m.content }],
  }));

  const result = await model.generateContentStream({
    contents,
    generationConfig: {
      temperature: options.temperature ?? 0.7,
      maxOutputTokens: options.max_tokens ?? 1024,
    },
  });

  // Wrap Gemini stream into async iterator matching OpenAI chunk shape
  async function* iterator() {
    for await (const chunk of result.stream) {
      const text = chunk.text();
      if (!text) continue;
      yield {
        choices: [
          { delta: { content: text } }
        ]
      };
    }
  }

  return iterator();
}

// Helper: Try Groq first, fallback to Gemini
async function getModelStream(messages, options = {}) {
  if (process.env.GROQ_API_KEY) {
    try {
      console.log("Using Groq (primary)");
      const stream = await createGroqStream(messages, options);
      return { stream, provider: "groq" };
    } catch (err) {
      console.warn("Groq failed, falling back to Gemini:", err.message);
    }
  }

  if (!process.env.GEMINI_API_KEY) {
    throw new Error("No GEMINI_API_KEY configured");
  }
  console.log("Using Gemini (fallback)");
  const stream = await createGeminiStream(messages, options);
  return { stream, provider: "gemini" };
}

export async function POST(request) {
  try {
    const { prompt, enableWebSearch = true } = await request.json();
    
    if (!prompt) {
      throw new Error("No prompt provided");
    }

    // Log API call attempt
    console.log("Processing chat request with prompt:", prompt.substring(0, 100) + "...");

    // Set system context for financial advisor role
    const messages = [
      {
        role: "system",
        content: `You are an expert financial advisor with deep knowledge of mutual funds, stocks, and investment strategies.
          
          IMPORTANT FORMATTING INSTRUCTIONS:
          - DO NOT use hash symbols (#) or asterisks (**) for headings
          - Use simple UPPERCASE TEXT for section titles (e.g., KEY POINTS)
          - Use bullet points (•) or dashes (-) for all lists and sub-points
          - Keep formatting clean and easy to read
          - Headings should be plain text without any special formatting
          
          Response Guidelines:
          • Keep responses short and focused on the user's question
          • Use simple language, avoiding technical jargon
          • Format advice in clear, numbered points or bullet points
          - Prioritize recent and reliable financial information
          - Always cite sources when using current market data or recent news
          • If uncertain, be transparent about limitations
          • Focus on educational guidance, not specific investment advice
          • Stay professional and factual in responses
          - When current market data is available, use it to provide more accurate insights`
      },
      { role: "user", content: prompt }
    ];

    // Get AI stream (Groq primary, Gemini fallback)
    const { stream: chatStream, provider } = await getModelStream(messages, {
      temperature: 1,
      max_tokens: 1024,
    });
    console.log("AI provider:", provider);
    return createStreamResponse(chatStream);

    // Helper function to create stream response
    function createStreamResponse(chatStream) {
      const stream = new ReadableStream({
        async start(controller) {
          try {
            for await (const chunk of chatStream) {
              const content = chunk.choices[0]?.delta?.content || "";
              if (content) {
                controller.enqueue(new TextEncoder().encode(content));
              }
            }
            controller.close();
          } catch (error) {
            console.error("Stream error:", error);
            controller.error(error);
          }
        },
      });

      return new Response(stream, {
        headers: {
          "Content-Type": "text/plain",
          "Cache-Control": "no-cache",
        },
      });
    }

  } catch (error) {
    console.error("Chat API error:", {
      message: error.message,
      name: error.name,
      stack: error.stack,
    });

    if (error.message === "No prompt provided") {
      return NextResponse.json(
        { error: "Please provide a question or message" },
        { status: 400 }
      );
    }

    if (error.message?.includes('401')) {
      return NextResponse.json(
        { error: "Authentication failed with the chat service" },
        { status: 401 }
      );
    }

    if (error.message?.includes('429')) {
      return NextResponse.json(
        { error: "Too many requests. Please try again later." },
        { status: 429 }
      );
    }

    // Handle web search specific errors
    if (error.message?.includes('web search')) {
      return NextResponse.json(
        { error: "Web search is temporarily unavailable. Try again later." },
        { status: 503 }
      );
    }

    return NextResponse.json(
      { error: error.message || "Failed to process chat request" },
      { status: 500 }
    );
  }
}