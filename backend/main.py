import os
import json
import base64
import logging
import asyncio
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("makanmap")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GMI_API_KEY = os.environ.get("GMI_API_KEY", "")
GMI_BASE_URL = "https://api.gmi-serving.com/v1"

MAX_RETRIES = 3
RETRY_BACKOFF = [2, 4, 8]  # seconds between retries


async def call_gmi_api(payload: dict, timeout: int, step_label: str) -> dict:
    """Call GMI API with retry logic, backoff, and detailed logging."""
    model = payload.get("model", "unknown")
    log.info("[%s] Calling model=%s (timeout=%ds)", step_label, model, timeout)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log.info("[%s] Attempt %d/%d — model=%s", step_label, attempt, MAX_RETRIES, model)
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    f"{GMI_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {GMI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

            if resp.status_code != 200:
                log.error(
                    "[%s] Attempt %d/%d failed — model=%s, status=%d, body=%s",
                    step_label, attempt, MAX_RETRIES, model, resp.status_code, resp.text,
                )
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_BACKOFF[attempt - 1])
                    continue
                raise HTTPException(status_code=502, detail=f"{step_label} API error (status {resp.status_code}): {resp.text}")

            result = resp.json()
            content = result["choices"][0]["message"]["content"]
            log.info("[%s] Attempt %d/%d succeeded — model=%s, response_length=%d chars",
                     step_label, attempt, MAX_RETRIES, model, len(content))
            log.info("[%s] Response:\n%s", step_label, content)
            return result

        except httpx.TimeoutException:
            log.error("[%s] Attempt %d/%d timed out — model=%s, timeout=%ds",
                      step_label, attempt, MAX_RETRIES, model, timeout)
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF[attempt - 1])
                continue
            raise HTTPException(status_code=502, detail=f"{step_label} timed out after {MAX_RETRIES} attempts")

        except (KeyError, IndexError) as e:
            log.error("[%s] Attempt %d/%d unexpected response — model=%s, error=%s, body=%s",
                      step_label, attempt, MAX_RETRIES, model, e, resp.text)
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF[attempt - 1])
                continue
            raise HTTPException(status_code=502, detail=f"{step_label} unexpected response: {e}")

    raise HTTPException(status_code=502, detail=f"{step_label} failed after {MAX_RETRIES} attempts")


@app.get("/health")
def health():
    return {"status": "ok"}


# --- Image Parsing (smart classification) ---

class ParseImageRequest(BaseModel):
    image_base64: str


STRUCTURING_SYSTEM_PROMPT = (
    "You are a data extraction assistant for a Singapore hawker stall marketing tool. "
    "You receive raw text extracted from photos of a hawker stall or restaurant. "
    "Your job is to interpret the raw text, identify what each piece of information is, "
    "and organize it into a clean structured JSON response. "
    "Return ONLY valid JSON — no explanation, no markdown, no code fences."
)

STRUCTURING_USER_PROMPT = """Below is raw text extracted from a photo of a hawker stall or restaurant in Singapore.
The text is unstructured — it may contain stall names, dish names, prices, addresses, certifications, or other details all mixed together.

Your job: read through all the raw text, figure out what each piece of information represents, and organize it into structured JSON.

--- RAW TEXT FROM IMAGE ---
{vision_text}
--- END ---

Return a JSON object with this exact structure (include only fields that have actual data):

{{
  "image_type": "menu" | "stall" | "food" | "other",
  "stall_name": string or null,
  "address": string or null,
  "cuisine_type": string or null,
  "description": string or null,
  "dishes": [
    {{
      "name": "Dish Name",
      "sizes": [{{"label": "Regular", "price": "$X.XX"}}]
    }}
  ],
  "tags": ["Halal", "Michelin Bib Gourmand", ...],
  "notes": string or null
}}

Rules:
- "image_type": classify what the original photo shows (menu board, stall front, food close-up, or other).
- Every dish MUST have a "sizes" array. This keeps the structure consistent.
  - Single price (e.g. "$5"): sizes: [{{"label": "Regular", "price": "$5"}}]
  - Two prices (e.g. "$12/15"): sizes: [{{"label": "Regular", "price": "$12"}}, {{"label": "Large", "price": "$15"}}]
  - Three prices (e.g. "$12/15/20"): sizes: [{{"label": "Small", "price": "$12"}}, {{"label": "Medium", "price": "$15"}}, {{"label": "Large", "price": "$20"}}]
- "tags" should capture dietary/certification info: Halal, No Pork No Lard, MUIS Certified, Muslim-Owned, Vegetarian, Vegan, No MSG, Michelin Star, Bib Gourmand, Michelin Selected.
- "notes" for anything else useful: opening hours, phone numbers, specialties, slogans.

Return valid JSON only."""


@app.post("/api/parse-image")
async def parse_image(req: ParseImageRequest):
    if not GMI_API_KEY:
        raise HTTPException(status_code=500, detail="GMI_API_KEY not set")

    # --- Step 1: Gemini vision — free-form analysis (no JSON requirement) ---
    vision_payload = {
        "model": "google/gemini-3.1-pro-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{req.image_base64}"
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "OCR this image of a food stall or restaurant in Singapore.\n"
                            "Output the restaurant/stall name if visible.\n"
                            "For each dish, output one line: DISH NAME | PRICE\n"
                            "IMPORTANT: Whenever you see a $ symbol or any number near a dish, "
                            "that is the price — always include it. Never skip prices.\n"
                            "For prices with slashes like '$12/15/20', write them exactly as shown.\n"
                            "Also note any visible tags, certifications, or stickers "
                            "(Halal, Michelin, No Pork No Lard, etc.) as separate lines.\n"
                            "Note any address, opening hours, or phone numbers.\n\n"
                            "Do not explain. Do not think. Just list what you see."
                        ),
                    },
                ],
            }
        ],
        "max_tokens": 4000,
        "temperature": 0,
    }

    log.info("[parse-image] Step 1: Sending image to Gemini (image_size=%d bytes)", len(req.image_base64))
    result1 = await call_gmi_api(vision_payload, timeout=120, step_label="parse-image Step 1")
    vision_text = result1["choices"][0]["message"]["content"]

    # --- Step 2: GPT-5.4-mini — structure into clean JSON ---
    structure_payload = {
        "model": "openai/gpt-5.4-mini",
        "messages": [
            {"role": "system", "content": STRUCTURING_SYSTEM_PROMPT},
            {"role": "user", "content": STRUCTURING_USER_PROMPT.format(vision_text=vision_text)},
        ],
        "max_completion_tokens": 2000,
        "temperature": 0,
    }

    log.info("[parse-image] Step 2: Structuring with GPT-5.4-mini")
    result2 = await call_gmi_api(structure_payload, timeout=60, step_label="parse-image Step 2")

    try:
        content = result2["choices"][0]["message"]["content"]
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        parsed = json.loads(content)
        log.info("[parse-image] Final result: type=%s, dishes=%d, tags=%s",
                 parsed.get("image_type"), len(parsed.get("dishes", [])), parsed.get("tags", []))
    except json.JSONDecodeError as e:
        log.error("[parse-image] JSON parse failed: %s\nContent:\n%s", e, content)
        raise HTTPException(status_code=502, detail=f"Failed to parse structured JSON: {e}")

    return parsed


# --- Task 3: Copy Generation ---

class DishSize(BaseModel):
    label: str
    price: Optional[str] = ""


class Dish(BaseModel):
    name: str
    price: Optional[str] = ""
    sizes: list[DishSize] = []


class GenerateCopyRequest(BaseModel):
    stall_name: str
    cuisine_type: str = ""
    dishes: list[Dish] = []
    description: str = ""


@app.post("/api/generate-copy")
async def generate_copy(req: GenerateCopyRequest):
    log.info("[generate-copy] Request: stall=%s, cuisine=%s, dishes=%d, desc=%s",
             req.stall_name, req.cuisine_type, len(req.dishes), req.description[:100] if req.description else "")
    if not GMI_API_KEY:
        raise HTTPException(status_code=500, detail="GMI_API_KEY not set")

    def format_dish(d):
        if d.sizes:
            sizes_str = " / ".join(f"{s.label}: {s.price}" for s in d.sizes)
            return f"- {d.name} ({sizes_str})"
        elif d.price:
            return f"- {d.name} ({d.price})"
        return f"- {d.name}"

    dish_list = "\n".join(format_dish(d) for d in req.dishes)
    stall_info = f"Name: {req.stall_name}\nCuisine: {req.cuisine_type}\nMenu:\n{dish_list}"
    if req.description:
        stall_info += f"\nDescription: {req.description}"

    payload = {
        "model": "google/gemini-3.1-pro-preview",
        "messages": [
            {
                "role": "system",
                "content": "You are a marketing copywriter for small food businesses in Singapore. Always return valid JSON only.",
            },
            {
                "role": "user",
                "content": (
                    f"Stall Info:\n{stall_info}\n\n"
                    "Generate marketing copy in three languages: English, Simplified Chinese, and Bahasa Melayu.\n"
                    "For each language, write:\n"
                    "1. An Instagram caption (150-200 words, warm tone, 5-8 relevant hashtags, ends with a call to action)\n"
                    "2. A Google Maps business description (80-120 words, factual, keyword-rich, highlights best dishes)\n"
                    "3. A WhatsApp broadcast message (60-80 words, friendly tone, suitable for sending to regulars)\n\n"
                    "Return as JSON:\n"
                    '{ "en": { "instagram": "...", "google_maps": "...", "whatsapp": "..." },\n'
                    '  "zh": { "instagram": "...", "google_maps": "...", "whatsapp": "..." },\n'
                    '  "bm": { "instagram": "...", "google_maps": "...", "whatsapp": "..." } }\n\n'
                    "Only return valid JSON."
                ),
            },
        ],
        "max_tokens": 3000,
        "temperature": 0.7,
    }

    log.info("[generate-copy] Generating marketing copy for stall=%s", req.stall_name)
    result = await call_gmi_api(payload, timeout=90, step_label="generate-copy")

    try:
        content = result["choices"][0]["message"]["content"]
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        log.error("[generate-copy] JSON parse failed: %s\nContent:\n%s", e, content)
        raise HTTPException(status_code=502, detail=f"Failed to parse API response: {e}")

    return parsed


# --- Task 4: Marketing Card Image Generation ---

class GenerateCardRequest(BaseModel):
    stall_name: str
    cuisine_type: str
    address: str = ""
    dishes: list[Dish] = []
    tags: list[str] = []
    en_text: str = ""
    zh_text: str = ""
    bm_text: str = ""


def extract_image_from_response(result: dict) -> Optional[str]:
    """Extract base64 image data from a Gemini response. Returns data URI or None."""
    try:
        content = result["choices"][0]["message"]["content"]

        # Case 1: content is a list of parts (multimodal response)
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    url = part.get("image_url", {}).get("url", "")
                    if url:
                        return url
                if isinstance(part, dict) and "inline_data" in part:
                    mime = part["inline_data"].get("mime_type", "image/png")
                    data = part["inline_data"].get("data", "")
                    if data:
                        return f"data:{mime};base64,{data}"

        # Case 2: content is a string containing a data URI
        if isinstance(content, str) and "base64," in content:
            idx = content.find("data:image")
            if idx >= 0:
                end = content.find('"', idx)
                if end < 0:
                    end = content.find("'", idx)
                if end < 0:
                    end = content.find("\n", idx)
                if end < 0:
                    end = len(content)
                return content[idx:end].strip()

    except (KeyError, IndexError) as e:
        log.error("[extract-image] Failed to extract image: %s", e)

    return None


@app.post("/api/generate-card")
async def generate_card(req: GenerateCardRequest):
    if not GMI_API_KEY:
        raise HTTPException(status_code=500, detail="GMI_API_KEY not set")

    prompt = f"""Generate a visually striking marketing card image for a Singapore hawker stall.

STALL: {req.stall_name}
CUISINE: {req.cuisine_type}
LOCATION: {req.address or "Singapore"}
TAGS: {", ".join(req.tags) if req.tags else "Local favourite"}

The card should have THREE horizontal blocks stacked vertically (1080x1350 pixels, 4:5 portrait):

BLOCK 1 — TOP (English, warm orange #E85D26 background):
Big bold white text: "{req.en_text or req.stall_name + ' — Authentic ' + req.cuisine_type}"
Small white subtext: "{req.stall_name} | {req.address or 'Singapore'}"

BLOCK 2 — MIDDLE (Dark navy #1A2E5A background):
Big bold white Chinese text: "{req.zh_text or req.stall_name}"
Small white subtext: "{req.stall_name}"

BLOCK 3 — BOTTOM (Forest green #2D6A4F background):
Big bold white Malay text: "{req.bm_text or req.stall_name}"
Small white subtext: "{req.stall_name}"

Style: Clean, modern, flat design. Bold sans-serif typography. Each block is clearly separated. Text should be large and readable. No photos — purely typographic. Add subtle texture or pattern for visual interest. Professional quality suitable for Instagram and WhatsApp sharing."""

    payload = {
        "model": "google/gemini-3.1-pro-preview",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 4096,
        "temperature": 0.9,
        "response_modalities": ["IMAGE", "TEXT"],
        "modalities": ["text", "image"],
    }

    log.info("[generate-card] Generating multilingual card for stall=%s", req.stall_name)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log.info("[generate-card] Attempt %d/%d", attempt, MAX_RETRIES)
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"{GMI_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {GMI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

            if resp.status_code != 200:
                log.error("[generate-card] Attempt %d failed: status=%d, body=%s",
                          attempt, resp.status_code, resp.text[:500])
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_BACKOFF[attempt - 1])
                    continue
                raise HTTPException(status_code=502, detail=f"Image generation failed (status {resp.status_code})")

            result = resp.json()
            log.info("[generate-card] Response content type: %s",
                     type(result.get("choices", [{}])[0].get("message", {}).get("content")))

            image_data = extract_image_from_response(result)
            if image_data:
                log.info("[generate-card] Successfully extracted image (%d chars)", len(image_data))
                return {"image_base64": image_data, "status": "success"}

            # No image extracted — log and retry
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            log.warning("[generate-card] No image in response. Content preview: %s",
                        str(content)[:300])
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF[attempt - 1])
                continue

            return {"image_base64": None, "status": "unsupported",
                    "message": "Gemini did not return an image. Use HTML fallback."}

        except httpx.TimeoutException:
            log.error("[generate-card] Attempt %d timed out", attempt)
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF[attempt - 1])
                continue
            raise HTTPException(status_code=502, detail="Image generation timed out")
