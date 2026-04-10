# MakanMap — Architecture

## Overview

MakanMap is a two-sided platform for Singapore's hawker ecosystem. Stall owners snap a photo of their menu to go live in minutes; consumers get a real-time map of what's open, what's on the menu, and how to get there — in three languages (EN, ZH, BM).

The MVP (built at the GMI Cloud x Z.ai Singapore Hackathon 2025) covers the **stallholder onboarding side**: upload photos, AI extracts stall info and menu items, then generates ready-to-publish marketing copy for Instagram, Google Maps, and WhatsApp.

**One onboarding flow feeds both sides.** Every menu upload automatically populates the public discovery layer — no separate data entry, no admin overhead.

## Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | React 18 + Tailwind CSS (via CDN) | Zero build step, single file, fast iteration |
| Backend | Python FastAPI | Async, lightweight, easy API proxying |
| Vision AI | Gemini 3.1 Pro (via GMI Cloud) | Best-in-class image OCR |
| JSON Structuring | GPT-5.4-mini (via GMI Cloud) | Reliable structured output from raw OCR text |
| Copy Generation | GLM-5.1 / glm-5-fp8 (via GMI Cloud) | Strong multilingual generation (hackathon sponsor) |
| API Gateway | GMI Cloud Inference Engine | Unified OpenAI-compatible API for all models |

### Future Stack (Consumer Side)

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Map Rendering | SLA OneMap SDK | Singapore government map with barrier-free routing |
| Base Data | NEA Open Data | Hawker centre and stall registry |
| Geospatial | PostGIS + Redis | Location queries + real-time open status cache |
| Stallholder Fallback | Telegram Bot | Low-friction daily open/closed toggle |

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
  makanmap.log           — Backend logs (gitignored)
```

## How It Works

| Step | Who | Action | Output |
|------|-----|--------|--------|
| **1. SNAP** | Stallholder | Upload photo of menu, stall front, or food | Raw text extracted via OCR |
| **2. EXTRACT** | AI Pipeline | Gemini OCR + GPT-5.4-mini structuring | Structured stall profile (dishes, prices, tags) |
| **3. REVIEW** | Stallholder | Edit dish names, prices, dietary tags | Confirmed menu data |
| **4. PUBLISH** | Stallholder | One-tap: generate marketing copy | IG / Google Maps / WhatsApp copy in 3 languages |

## API Endpoints

### `GET /health`
Health check. Returns `{ "status": "ok" }`.

### `POST /api/parse-image`
Analyzes an uploaded photo using a two-step AI pipeline.

**Request:** `{ "image_base64": string }`

**Pipeline:**
1. **Gemini 3.1 Pro** — OCR extraction. Reads all visible text from the image (stall name, dish names, prices, tags, certifications) in a flat `DISH NAME | PRICE` format. Temperature=0, no interpretation.
2. **GPT-5.4-mini** — Takes the raw OCR text and structures it into clean JSON. Temperature=0 for deterministic output.

Both steps use a retry mechanism (3 attempts, 2/4/8s backoff) with extended timeouts (120s vision, 60s structuring).

**Response:**
```json
{
  "image_type": "menu | stall | food | other",
  "stall_name": "string | null",
  "address": "string | null",
  "cuisine_type": "string | null",
  "description": "string | null",
  "dishes": [
    { "name": "Char Kway Teow", "sizes": [
      { "label": "Regular", "price": "$4.00" }
    ]},
    { "name": "Fried Rice", "sizes": [
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
                         │    (OCR text extraction)  │
                         │                          │
                         │  Step 2: GPT-5.4-mini    │──> GMI Cloud (text)
                         │    (interpret + JSON)     │
                         └──────────┬───────────────┘
                                    │ structured JSON
                                    ▼
                         ┌──────────────────────────┐
                         │  Frontend merges result   │
                         │  into stall profile:      │
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

1. **Two-step vision pipeline** — Gemini does pure OCR (extract text exactly as shown), GPT-5.4-mini does all the interpretation and JSON structuring. Splitting OCR from structuring eliminated hallucinated data and JSON parse errors. Temperature=0 on both steps for deterministic output.

2. **Retry with backoff** — All API calls retry up to 3 times with 2/4/8s backoff. Vision timeout is 120s, structuring 60s, copy generation 90s. Handles intermittent GMI Cloud timeouts gracefully.

3. **Cumulative profile (merge, not replace)** — Each photo upload adds to the stall profile rather than overwriting it. Stall name fills once; dishes always append. Users can upload a stall photo, then a menu photo, and the profile builds up.

4. **No build tools** — React and Tailwind via CDN, Babel transpiles JSX in-browser. Zero setup, single `python3 -m http.server` for frontend. Acceptable for a hackathon demo.

5. **Frontend state as the "DB"** — No database, no persistence. All stall profile data lives in React useState. Sufficient for a single-session demo tool. Future: PostGIS + Redis for persistent stall profiles and real-time open status.

6. **Singapore-specific intelligence** — Price shorthand parsing ($12/15/20 = portion sizes), dietary tag detection (Halal, No Pork No Lard, MUIS), Michelin recognition. These are domain-specific features that make the tool genuinely useful for hawker stall owners.

7. **Consistent dish pricing structure** — All dishes use a `sizes` array: single-price items get `[{"label": "Regular", "price": "$X"}]`, two prices get Regular/Large, three get Small/Medium/Large. This unified structure simplifies frontend rendering and editing.

8. **Missing price indicators** — When OCR fails to extract a price, the frontend highlights the dish with an amber border and "Price missing — please add it" prompt, guiding the user to fill in gaps manually.

## Smart Nation Alignment

MakanMap sits adjacent to existing Smart Nation infrastructure:

| Existing Solution | MakanMap Complement |
|-------------------|---------------------|
| Barrier-Free Access Routing (SLA) | Links accessible routes to nearest open hawker stall |
| Smart Parking (HDB) | Applies same real-time status model to stall availability |
| Lived Experience pillar | Adds hawker culture — Singapore's UNESCO heritage — as a live data layer |

## Running

```bash
# Set your API key
echo 'GMI_API_KEY="your-key"' > .env

# Start both servers
./run.sh

# View logs
tail -f makanmap.log

# Open the app
open http://localhost:3000
```
