# HawkerBoost

**AI-powered marketing assistant for Singapore hawker stall owners and small F&B businesses.**

Built at the GMI Cloud x Z.ai Singapore Hackathon 2025.

---

## The Problem

Singapore's hawker culture is a national institution — over 6,000 stalls across 110+ hawker centres. The vast majority are small, independent, and time-poor.

- **No digital presence** — Most stalls have no Instagram, no Google Maps listing, no online menu. They lose visibility to food-discovery apps and tourists.
- **Language barrier** — Singapore's multicultural market needs copy in English, Chinese, and Malay. Most owners are fluent in only one.
- **Time cost** — Writing platform-specific captions with the right tone, hashtags, and formatting is a skill most hawker owners don't have and can't afford to hire for.
- **High friction tools** — Existing tools (Canva, ChatGPT, Google Translate) require multiple steps, accounts, and context-switching — too complex for a stall owner managing a lunch rush.

## The Solution

HawkerBoost takes a photo of your menu and generates ready-to-publish marketing copy for **3 platforms** in **3 languages** — in under 30 seconds, with zero sign-up.

**How it works:**

1. **Snap** — Upload photos of your menu, stall front, or food (up to 5)
2. **Extract** — AI reads the image and pulls out stall name, dishes, prices, dietary tags, and Michelin recognition
3. **Generate** — One tap produces copy-paste-ready text for Instagram, Google Maps, and WhatsApp in English, Chinese, and Bahasa Melayu

**Built for real hawker stall owners:**
- Understands Singapore price formats ($12/15/20 = portion sizes)
- Detects Halal, No Pork No Lard, MUIS certification, Michelin Bib Gourmand
- Highlights missing prices so the user can fill them in
- No accounts, no installs — works on any mobile browser

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Tailwind CSS (CDN, zero build step) |
| Backend | Python FastAPI |
| Vision OCR | Gemini 3.1 Pro (via GMI Cloud) |
| JSON Structuring | GPT-5.4-mini (via GMI Cloud) |
| Copy Generation | GLM-5.1 / glm-5-fp8 (via GMI Cloud) |

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

*HawkerBoost — Built in 6 hours. Designed for 6,000 stalls.*
