

# WealthPulse

WealthPulse is an AI-powered portfolio cockpit for Indian retail investors. Track stocks, mutual funds, and crypto in one place, see real risk/return analytics, and get conversational guidance from AI Dost and AI Report. 

---

## What you can do

* **Track everything in one dashboard**

  * Add stocks, mutual funds, and crypto with buy price, quantity, and buy date.
  * See aggregated positions (average buy price, total quantity) instead of scattered lots.
  * View per-holding and overall P&L, XIRR, and timeline charts.

* **See real market behaviour**

  * Live prices via:

    * Binance WebSocket (crypto → Redis).
    * Finnhub WebSocket (US stocks → Redis).
    * yfinance polling (Indian stocks → Redis).
  * MF NAVs parsed directly from the AMFI NAV text file and stored in `price_history`.

* **Understand risk, not just returns**

  * Volatility, Sharpe ratio, and max drawdown per asset using daily price history.
  * 1-year Monte Carlo simulation for each holding, cached in Redis for fast access.
  * Daily portfolio snapshots so you can see how total value evolved over time.

* **Talk to your portfolio**

  * **AI Dost**: friendly assistant that explains your portfolio in simple language and suggests next steps.
  * **AI Report**: professional-style report with allocation, risk assessment, and performance by asset.
  * Both use Groq (Llama-3.3-70B) with automatic Gemini fallback.

---

## How pricing & history work (in short)

* **Live data:**
  Workers connect to live sources and push prices into Redis:

  * Crypto → Binance WebSocket.
  * US stocks → Finnhub WebSocket.
  * Indian stocks → periodic yfinance polling.
  * Mutual funds → NAVs parsed from AMFI and cached.

* **Why backfill “old” data?**
  Advanced metrics (volatility, Sharpe, drawdown, Monte Carlo) and charts need a *price series*, not just today’s price. So when a symbol appears in your holdings, backfill jobs fetch ~months of historical prices into `price_history`. That allows:

  * Realistic volatility and Sharpe (instead of always 0).
  * Max drawdown over time.
  * Monte Carlo simulations based on actual past behaviour, not guesses.

* **Combining it all:**
  When you open the portfolio:

  * Analytics layer reads your holdings and groups all buys of the same symbol.
  * It uses Redis for current prices and `price_history` for daily history.
  * It computes P&L, XIRR (from all buy dates to today), risk metrics, and Monte Carlo outputs.
  * AI endpoints read that analytics summary and generate human-readable explanations.

---

## API overview (backend)

Base URL (local): `http://localhost:8000`

### Portfolio

* `GET /api/portfolio`
  List all holdings for the current user.

* `POST /api/portfolio`
  Add a holding (symbol, name, assettype, buyprice, quantity, buydate).

* `DELETE /api/portfolio/holding/{id}`
  Remove a specific lot.

* `GET /api/portfolio/history/{symbol}`
  Full buy history (all lots) for a symbol for the current user.

### Analytics

* `GET /api/analytics/portfolio`
  Aggregated portfolio analytics:

  * Summary (invested, current value, total P&L, P&L %).
  * Holdings (one per symbol) with P&L, XIRR, risk metrics, Monte Carlo.

* `GET /api/analytics/history`
  Portfolio value over time from daily snapshots.

### Market data

* `GET /api/market/mutualfunds?q=…` – MF search.
* `GET /api/market/mutualfunds/{schemecode}` – MF NAV history.
* `GET /api/market/stocks/india?symbol=…` – Indian stock price (cached).
* `GET /api/market/stocks/us?symbol=…` – US stock price (cached).
* `GET /api/market/crypto?symbol=…` – Crypto price (cached).

### Streaming

* `GET /api/stream/prices`
  Server-Sent Events stream of live prices from Redis.

### AI

* `GET /api/ai/dost`
  Friendly AI overview of your portfolio.

* `GET /api/ai/report`
  Structured AI report (`{ text, format: "markdown" }`).

All protected endpoints expect an Auth0 access token in the `Authorization: Bearer` header.

---

## Environment configuration

### Backend `.env`

```bash
# ── Copy this file to .env and fill in the real values ───────────────

# PostgreSQL connection (asyncpg driver)
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DATABASE?sslmode=require

# Redis
REDIS_URL=redis://localhost:6379

# Auth0 (from Auth0 Dashboard → Applications → your app)
AUTH0_DOMAIN=dev-qt0cqogfgwebky55.us.auth0.com
AUTH0_AUDIENCE=YOUR_AUTH0_CLIENT_ID   # must match the `aud` claim in the access token

# External APIs
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
FINNHUB_API_KEY=your_finnhub_key

# CORS — set this to your real Vercel deployment URL
FRONTEND_URL=https://wealthpulse.vercel.app
```

### Frontend `.env.local`

```bash
# Auth0 Configuration for Next.js
AUTH0_SECRET=your_secret_key_here
AUTH0_BASE_URL=http://localhost:3000
AUTH0_ISSUER_BASE_URL=https://your-auth0-domain.us.auth0.com
AUTH0_CLIENT_ID=your_client_id_here
AUTH0_CLIENT_SECRET=your_client_secret_here

# API Keys (for frontend AI routes, if used)
GROQ_API_KEY=your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Backend URL
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Getting started

### 1. Clone the repo

```bash
git clone https://github.com/your-user/wealthpulse.git
cd wealthpulse
```

### 2. Backend (FastAPI)

```bash
cd backend

# Create virtualenv
python -m venv venv
# Activate (Windows)
source venv/Scripts/activate
# or on Unix/macOS: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure env
cp .env.example .env
# edit .env with your DB, Redis, Auth0, and API keys

# Apply migrations (if needed)
alembic upgrade head

# Run backend
uvicorn main:app --reload
```

Backend will run on `http://localhost:8000`.

### 3. Frontend (Next.js)

```bash
cd frontend

# Install deps
npm install

# Create env
cp .env.local.example .env.local   # if you add an example file
# or just create .env.local and fill the values above

# Run dev server
npm run dev
```

Frontend will run on `http://localhost:3000` and proxy API calls to the backend (via `NEXT_PUBLIC_API_URL` and Next.js rewrites).

---
