# HawkerBoost — Architecture

## Overview

HawkerBoost is a mobile-first web app that helps Singapore hawker stall owners generate marketing copy. The user uploads photos (menu, stall front, food) and the AI extracts stall info, menu items, dietary tags, and Michelin recognition. When ready, it generates copy for Instagram, Google Maps, and WhatsApp in three languages (EN, ZH, BM).

## Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | React 18 + Tailwind CSS (via CDN) | Zero build step, single file, fast iteration |
| Backend | Python FastAPI | Async, lightweight, easy API proxying |
| Vision AI | Gemini 3.1 Pro (via GMI Cloud) | Best-in-class image understanding |
| JSON Structuring | GPT-5.4-mini (via GMI Cloud) | Reliable structured output from free-form text |
| Copy Generation | GLM-5.1 / glm-5-fp8 (via GMI Cloud) | Strong multilingual generation (hackathon sponsor) |
| API Gateway | GMI Cloud Inference Engine | Unified OpenAI-compatible API for all models |

## Project Structure

```
gmi/
  backend/
    main.py              — FastAPI app, 3 endpoints, all AI logic
    requirements.txt     — fastapi, uvicorn, httpx, python-multipart
  frontend/
    index.html           — Shell with React/Tailwind CDN imports
    app.jsx              — Entire UI in one file (Babel transpiled in-browser)
    backup-response.json — Cached demo fallback
  run.sh                 — Starts both servers, sources .env, logs to file
  .env                   — GMI_API_KEY (gitignored)
  hawkerboost.log        — Backend logs (gitignored)
```

## API Endpoints

### `GET /health`
Health check. Returns `{ "status": "ok" }`.

### `POST /api/parse-image`
Analyzes an uploaded photo using a two-step AI pipeline.

**Request:** `{ "image_base64": string }`

**Pipeline:**
1. **Gemini 3.1 Pro** — Analyzes the image in free-form text. Describes stall name, dishes, prices, tags, Michelin status, etc. No JSON requirement.
2. **GPT-5.4-mini** — Takes Gemini's description and structures it into clean JSON. Temperature=0 for deterministic output.

**Response:**
```json
{
  "image_type": "menu | stall | food | other",
  "stall_name": "string | null",
  "address": "string | null",
  "cuisine_type": "string | null",
  "description": "string | null",
  "dishes": [
    { "name": "Char Kway Teow", "price": "$4.00" },
    { "name": "Fried Rice", "price": "", "sizes": [
      { "label": "Small", "price": "$8" },
      { "label": "Medium", "price": "$10" },
      { "label": "Large", "price": "$12" }
    ]}
  ],
  "tags": ["Halal", "Michelin Bib Gourmand"],
  "notes": "Open 10am-8pm, closed Mondays"
}
```

### `POST /api/generate-copy`
Generates marketing copy in 3 languages for 3 platforms.

**Request:**
```json
{
  "stall_name": "string",
  "cuisine_type": "string",
  "dishes": [{ "name": "string", "price": "string", "sizes": [...] }],
  "description": "string (optional)"
}
```

**Response:**
```json
{
  "en": { "instagram": "...", "google_maps": "...", "whatsapp": "..." },
  "zh": { "instagram": "...", "google_maps": "...", "whatsapp": "..." },
  "bm": { "instagram": "...", "google_maps": "...", "whatsapp": "..." }
}
```

## Data Flow

```
                         ┌──────────────────────────┐
  User uploads photos    │     Frontend (React)      │
  (up to 5 at once) ──> │  Single-page, mobile-first │
                         │  Cumulative stall profile  │
                         └──────────┬───────────────┘
                                    │ POST /api/parse-image (per photo)
                                    ▼
                         ┌──────────────────────────┐
                         │    FastAPI Backend        │
                         │                          │
                         │  Step 1: Gemini 3.1 Pro  │──> GMI Cloud (vision)
                         │    (free-form analysis)   │
                         │                          │
                         │  Step 2: GPT-5.4-mini    │──> GMI Cloud (text)
                         │    (JSON structuring)     │
                         └──────────┬───────────────┘
                                    │ structured JSON
                                    ▼
                         ┌──────────────────────────┐
                         │  Frontend merges result   │
                         │  into stall profile DB:   │
                         │  - Stall name, address    │
                         │  - Cuisine type           │
                         │  - Dishes + portion sizes │
                         │  - Tags (Halal, Michelin) │
                         │  - AI notes               │
                         └──────────┬───────────────┘
                                    │ User clicks "Generate Marketing Copy"
                                    │ POST /api/generate-copy
                                    ▼
                         ┌──────────────────────────┐
                         │  GLM-5.1 (glm-5-fp8)     │──> GMI Cloud
                         │  Generates 9 text blocks: │
                         │  3 platforms × 3 languages │
                         └──────────┬───────────────┘
                                    │
                                    ▼
                         ┌──────────────────────────┐
                         │  Results displayed inline │
                         │  EN / 中文 / BM tabs       │
                         │  Copy-to-clipboard buttons │
                         └──────────────────────────┘
```

## Key Design Decisions

1. **Two-step vision pipeline** — Gemini is great at understanding images but unreliable at producing valid JSON. GPT-5.4-mini is cheap and deterministic at JSON structuring. Splitting the work eliminated JSON parse errors.

2. **Cumulative profile (merge, not replace)** — Each photo upload adds to the stall profile rather than overwriting it. Stall name fills once; dishes always append. Users can upload a stall photo, then a menu photo, and the profile builds up.

3. **No build tools** — React and Tailwind via CDN, Babel transpiles JSX in-browser. Zero setup, single `python3 -m http.server` for frontend. Acceptable for a hackathon demo.

4. **Frontend state as the "DB"** — No database, no persistence. All stall profile data lives in React useState. Sufficient for a single-session demo tool.

5. **Singapore-specific intelligence** — Price shorthand parsing ($12/15/20 = portion sizes), dietary tag detection (Halal, No Pork No Lard, MUIS), Michelin recognition. These are domain-specific features that make the tool genuinely useful for hawker stall owners.

## Running

```bash
# Set your API key
echo 'GMI_API_KEY="your-key"' > .env

# Start both servers
./run.sh

# View logs
tail -f hawkerboost.log

# Open the app
open http://localhost:3000
```
