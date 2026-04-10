import os
import json
import logging
import asyncio
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("hawkerboost")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GMI_API_KEY = os.environ.get("GMI_API_KEY", "")
GMI_BASE_URL = "https://api.gmi-serving.com/v1"


@app.get("/health")
def health():
    return {"status": "ok"}


# --- Image Parsing (smart classification) ---

class ParseImageRequest(BaseModel):
    image_base64: str


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
                            "You are analyzing a photo related to a food stall or restaurant in Singapore.\n"
                            "Describe everything you see in detail. Include:\n\n"
                            "1. What type of image is this? (menu, stall front/signage, food photo, or other)\n"
                            "2. Stall/restaurant name if visible\n"
                            "3. Address or location if visible\n"
                            "4. Cuisine type\n"
                            "5. ALL menu items and their prices. IMPORTANT: prices like '$12/15/20' or '8/10/12' "
                            "mean different portion sizes (small/medium/large). List each size separately.\n"
                            "6. Any dietary tags: Halal, No Pork No Lard, MUIS certification, Muslim-owned, "
                            "Vegetarian, Vegan, No MSG\n"
                            "7. Michelin recognition: Michelin Star, Bib Gourmand, Michelin Selected "
                            "(look for red Michelin stickers/plaques)\n"
                            "8. Any other info: opening hours, phone numbers, slogans, specialties\n\n"
                            "Be thorough. List every dish and every price you can read."
                        ),
                    },
                ],
            }
        ],
        "max_tokens": 2000,
    }

    log.info("[parse-image] Step 1: Sending image to Gemini (image_size=%d bytes)", len(req.image_base64))

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{GMI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {GMI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=vision_payload,
            )
    except httpx.TimeoutException:
        log.error("[parse-image] Step 1 timed out")
        raise HTTPException(status_code=502, detail="Vision API timed out")

    if resp.status_code != 200:
        log.error("[parse-image] Step 1 failed: status=%d, body=%s", resp.status_code, resp.text)
        raise HTTPException(status_code=502, detail=f"Vision API error: {resp.text}")

    try:
        vision_text = resp.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        log.error("[parse-image] Step 1 unexpected response: %s", resp.text)
        raise HTTPException(status_code=502, detail=f"Unexpected vision API response: {e}")

    log.info("[parse-image] Step 1 done. Gemini output (%d chars):\n%s", len(vision_text), vision_text)

    # --- Step 2: GPT-5.4-mini — structure into clean JSON ---
    structure_payload = {
        "model": "openai/gpt-5.4-mini",
        "messages": [
            {
                "role": "system",
                "content": "You convert unstructured text descriptions of food stalls into structured JSON. Always return valid JSON only, no explanation, no markdown.",
            },
            {
                "role": "user",
                "content": (
                    "Here is a description of a food stall image. Convert it into this exact JSON structure.\n"
                    "Include only fields that have actual data — omit fields with no info.\n\n"
                    "Required JSON schema:\n"
                    "{\n"
                    '  "image_type": "menu" | "stall" | "food" | "other",\n'
                    '  "stall_name": string or null,\n'
                    '  "address": string or null,\n'
                    '  "cuisine_type": string or null,\n'
                    '  "description": string or null,\n'
                    '  "dishes": [{ "name": string, "price": string, "sizes": [{"label": string, "price": string}] }],\n'
                    '  "tags": [string],\n'
                    '  "notes": string or null\n'
                    "}\n\n"
                    "Rules:\n"
                    '- For dishes with multiple portion sizes, leave "price" empty and populate "sizes" array.\n'
                    '  Use "Small"/"Medium"/"Large" for 3 sizes, "Regular"/"Large" for 2 sizes.\n'
                    '- For single-price dishes, put the price in "price" and omit "sizes".\n'
                    '- Tags should include dietary/certification info: Halal, No Pork No Lard, Michelin Star, '
                    "Bib Gourmand, Michelin Selected, Vegetarian, etc.\n\n"
                    f"--- IMAGE DESCRIPTION ---\n{vision_text}\n--- END ---\n\n"
                    "Return valid JSON only."
                ),
            },
        ],
        "max_tokens": 2000,
        "temperature": 0,
    }

    log.info("[parse-image] Step 2: Sending to GPT-5.4-mini for JSON structuring")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp2 = await client.post(
                f"{GMI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {GMI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=structure_payload,
            )
    except httpx.TimeoutException:
        log.error("[parse-image] Step 2 timed out")
        raise HTTPException(status_code=502, detail="JSON structuring timed out")

    if resp2.status_code != 200:
        log.error("[parse-image] Step 2 failed: status=%d, body=%s", resp2.status_code, resp2.text)
        raise HTTPException(status_code=502, detail=f"Structuring API error: {resp2.text}")

    try:
        content = resp2.json()["choices"][0]["message"]["content"]
        log.info("[parse-image] Step 2 raw output:\n%s", content)
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        parsed = json.loads(content)
        log.info("[parse-image] Final result: type=%s, dishes=%d, tags=%s",
                 parsed.get("image_type"), len(parsed.get("dishes", [])), parsed.get("tags", []))
    except (KeyError, IndexError) as e:
        log.error("[parse-image] Step 2 unexpected response: %s", resp2.text)
        raise HTTPException(status_code=502, detail=f"Unexpected structuring response: {e}")
    except json.JSONDecodeError as e:
        log.error("[parse-image] Step 2 JSON parse failed: %s\nContent:\n%s", e, content)
        raise HTTPException(status_code=502, detail=f"Failed to parse structured JSON: {e}")

    return parsed


# --- Task 3: Copy Generation ---

class DishSize(BaseModel):
    label: str
    price: str


class Dish(BaseModel):
    name: str
    price: str = ""
    sizes: list[DishSize] = []


class GenerateCopyRequest(BaseModel):
    stall_name: str
    cuisine_type: str
    dishes: list[Dish]
    description: str = ""


@app.post("/api/generate-copy")
async def generate_copy(req: GenerateCopyRequest):
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
        "model": "glm-5-fp8",
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

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{GMI_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {GMI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"GMI API error: {resp.text}")

    try:
        content = resp.json()["choices"][0]["message"]["content"]
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        parsed = json.loads(content)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=502, detail=f"Failed to parse API response: {e}")

    return parsed
