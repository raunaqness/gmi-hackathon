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

    payload = {
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
                            "You are analyzing a photo related to a food stall or restaurant.\n"
                            "First, classify the image as one of: \"menu\", \"stall\", \"food\", or \"other\".\n\n"
                            "Then extract ALL relevant information you can see.\n\n"
                            "IMPORTANT — Menu price parsing rules:\n"
                            "Prices on hawker/restaurant menus are often written in shorthand for portion sizes:\n"
                            '- "$12/15/20" means Small: $12, Medium: $15, Large: $20\n'
                            '- "$5/$8" means Regular: $5, Large: $8\n'
                            '- "$3.50" means a single price\n'
                            '- "8/10/12" (no $ sign) still means prices in dollars\n'
                            "When you see multiple prices separated by / for one dish, split them into portion sizes.\n\n"
                            "Return a JSON object with these fields (include only fields you can extract):\n"
                            '- "image_type": one of "menu", "stall", "food", "other"\n'
                            '- "stall_name": name of the stall/restaurant if visible\n'
                            '- "address": address or location if visible (e.g. "Tiong Bahru Market, Stall #02-05")\n'
                            '- "cuisine_type": inferred cuisine (e.g. "Chinese", "Malay", "Indian", "Western")\n'
                            '- "description": any tagline, slogan, or description visible\n'
                            '- "dishes": array of dish objects. Each dish has:\n'
                            '    - "name": string\n'
                            '    - "price": string (single price like "$3.50", or empty if multiple sizes)\n'
                            '    - "sizes": array of {"label": string, "price": string} ONLY if multiple portion sizes exist\n'
                            '      e.g. [{"label": "Small", "price": "$12"}, {"label": "Medium", "price": "$15"}, {"label": "Large", "price": "$20"}]\n'
                            '      For 2 prices use "Regular" and "Large". For 3 use "Small", "Medium", "Large".\n'
                            '      Omit this field if there is only a single price.\n'
                            '- "tags": array of strings — dietary/certification tags visible or implied.\n'
                            '  Common Singapore hawker tags to look for:\n'
                            '  "Halal", "No Pork No Lard", "Halal-certified", "Muslim-owned",\n'
                            '  "Vegetarian", "Vegan", "No MSG", "Organic", "Kosher",\n'
                            '  "Michelin Bib Gourmand", "Michelin Star", "Michelin Selected".\n'
                            '  Look for: Halal/MUIS certification logos, "No Pork" signs,\n'
                            '  Michelin guide stickers/plaques (red Michelin logo), Bib Gourmand stickers.\n'
                            '  Only include tags you can actually see evidence of in the image.\n'
                            '- "notes": any other useful info (opening hours, phone number, specialties mentioned)\n\n'
                            "Only return valid JSON. No explanation."
                        ),
                    },
                ],
            }
        ],
        "max_tokens": 1500,
    }

    max_retries = 3
    last_error = None

    for attempt in range(1, max_retries + 1):
        log.info("[parse-image] Attempt %d/%d — sending to GMI API (model=%s, image_size=%d bytes)",
                 attempt, max_retries, payload["model"], len(req.image_base64))

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{GMI_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {GMI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

            log.info("[parse-image] Attempt %d — status=%d", attempt, resp.status_code)

            if resp.status_code != 200:
                last_error = f"GMI API error (HTTP {resp.status_code}): {resp.text}"
                log.warning("[parse-image] Attempt %d failed: %s", attempt, last_error)
                if attempt < max_retries:
                    await asyncio.sleep(2 * attempt)
                continue

            raw = resp.json()
            content = raw["choices"][0]["message"]["content"]
            log.info("[parse-image] Raw LLM content:\n%s", content)
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                content = content.rsplit("```", 1)[0]
            parsed = json.loads(content)
            log.info("[parse-image] Parsed result: type=%s, dishes=%d, tags=%s",
                     parsed.get("image_type"), len(parsed.get("dishes", [])), parsed.get("tags", []))
            return parsed

        except httpx.TimeoutException:
            last_error = f"Request timed out (attempt {attempt})"
            log.warning("[parse-image] %s", last_error)
            if attempt < max_retries:
                await asyncio.sleep(2 * attempt)
            continue
        except (KeyError, IndexError) as e:
            last_error = f"Unexpected API response: {e}"
            log.error("[parse-image] %s\nFull response: %s", last_error, resp.text)
            if attempt < max_retries:
                await asyncio.sleep(2 * attempt)
            continue
        except json.JSONDecodeError as e:
            last_error = f"LLM returned invalid JSON: {e}\nContent: {content}"
            log.error("[parse-image] %s", last_error)
            if attempt < max_retries:
                await asyncio.sleep(2 * attempt)
            continue

    log.error("[parse-image] All %d attempts failed. Last error: %s", max_retries, last_error)
    raise HTTPException(status_code=502, detail=f"Failed after {max_retries} attempts: {last_error}")


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
