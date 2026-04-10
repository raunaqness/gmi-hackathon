# MakanMap

**Singapore's Living Hawker Map — AI Onboarding x Real-Time Discovery**

*"Makan"* means "to eat" in Malay — widely adopted into Singlish as the go-to word for eating, dining, or grabbing a meal. *"Let's go makan"* means let's go eat. MakanMap is a map of where to makan.

Built at the GMI Cloud x Z.ai Singapore Hackathon 2025.

Made by [Raunaq](https://www.linkedin.com/in/gurraunaqsingh/) and [Viktoria](https://www.linkedin.com/in/viktoria-b-0a41aaa/)

---

## The Problem

Singapore's hawker culture is a national institution and UNESCO Intangible Cultural Heritage — over 6,000 stalls across 120+ hawker centres, serving millions of meals daily.

**For stall owners:**
- **No digital presence** — Most stalls have no Instagram, no Google Maps listing, no online menu. They lose visibility to food-discovery apps and tourists.
- **Language barrier** — Singapore's multicultural market needs copy in English, Chinese, and Malay. Most owners are fluent in only one.
- **Time cost** — Writing platform-specific captions with the right tone, hashtags, and formatting is a skill most owners don't have and can't afford to hire for.

**For consumers:**
- **No live information** — No way to know what's open right now, what's on the menu, or which stalls match dietary needs.
- **Fragmented data** — Renovation closures, queue times, and accessible routes are scattered across 4+ government portals.
- **Smart Nation gap** — Transport, parking, and accessibility are covered — but hawker culture has no live digital layer.

## The Solution

MakanMap is a two-sided platform: stall owners snap a menu photo to go live in minutes; consumers get a real-time map of what's open, what's on the menu, and how to get there — in three languages.

**One onboarding flow feeds both sides.** Every menu upload automatically populates the public discovery layer — no separate data entry, no admin overhead.

### How it works

| Step | Who | Action | Output |
|------|-----|--------|--------|
| **1. SNAP** | Stallholder | Upload photo of menu, stall front, or food | Raw text extracted via AI OCR |
| **2. EXTRACT** | AI Pipeline | Gemini OCR + GPT-5.4-mini structuring | Structured stall profile with dishes, prices, tags |
| **3. REVIEW** | Stallholder | Edit dish names, prices, dietary tags | Confirmed menu data |
| **4. PUBLISH** | Stallholder | One-tap: generate marketing copy | IG / Google Maps / WhatsApp copy in EN, ZH, BM |
| **5. DISCOVER** | Consumer | Filter live map by open now, diet, cuisine | Nearest open stalls with accessible route |

### Built for Singapore hawker stalls

- Understands Singapore price formats ($12/15/20 = portion sizes)
- Detects Halal, No Pork No Lard, MUIS certification, Michelin Bib Gourmand
- Highlights missing prices so users can fill them in
- No accounts, no installs — works on any mobile browser

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React 18 + Tailwind CSS (CDN) | Mobile-first UI, zero build step |
| Backend | Python FastAPI | Async API proxying |
| Vision OCR | Gemini 3.1 Pro (via GMI Cloud) | Menu photo text extraction |
| JSON Structuring | GPT-5.4-mini (via GMI Cloud) | Raw OCR to structured data |
| Copy Generation | GLM-5.1 / glm-5-fp8 (via GMI Cloud) | Multilingual marketing copy |
| Map (planned) | SLA OneMap SDK | Live hawker map with barrier-free routing |
| Base Data (planned) | NEA Open Data | Hawker centre and stall registry |

## Smart Nation Alignment

MakanMap fills the gap adjacent to existing Smart Nation infrastructure:

| Existing Solution | MakanMap Complement |
|-------------------|---------------------|
| Barrier-Free Access Routing (SLA) | Links accessible routes to nearest open hawker stall |
| Smart Parking (HDB) | Same real-time status model applied to stall availability |
| Lived Experience pillar | Adds hawker culture — UNESCO heritage — as a live data layer |

## Quick Start

```bash
# Set your API key
echo 'GMI_API_KEY="your-key"' > .env

# Start both servers
./run.sh

# Open the app
open http://localhost:3000
```

## Architecture

See [Architecture.md](Architecture.md) for the full technical breakdown, data flow diagrams, and design decisions.

---

*MakanMap — Built in 6 hours. Designed for 6,000 stalls.*
