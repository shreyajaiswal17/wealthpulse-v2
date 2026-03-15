import os
import httpx


async def call_ai(system: str, user: str) -> str:
    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            max_tokens=1024,
            temperature=0.7,
        )
        return response.choices[0].message.content

    except Exception as groq_err:
        print(f"⚠️ Groq failed: {groq_err}, falling back to Gemini...")
        api_key = os.getenv("GEMINI_API_KEY")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": f"{system}\n\n{user}"}]}]
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(url, json=payload, timeout=20)
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
