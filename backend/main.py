import os
import json
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
                            "Return a JSON object with these fields (include only fields you can extract):\n"
                            '- "image_type": one of "menu", "stall", "food", "other"\n'
                            '- "stall_name": name of the stall/restaurant if visible\n'
                            '- "address": address or location if visible (e.g. "Tiong Bahru Market, Stall #02-05")\n'
                            '- "cuisine_type": inferred cuisine (e.g. "Chinese", "Malay", "Indian", "Western")\n'
                            '- "description": any tagline, slogan, or description visible\n'
                            '- "dishes": array of {"name": string, "price": string} if menu items are visible\n'
                            '- "notes": any other useful info (opening hours, phone number, specialties mentioned)\n\n'
                            "Only return valid JSON. No explanation."
                        ),
                    },
                ],
            }
        ],
        "max_tokens": 1500,
    }

    async with httpx.AsyncClient(timeout=30) as client:
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


# --- Task 3: Copy Generation ---

class Dish(BaseModel):
    name: str
    price: str = ""


class GenerateCopyRequest(BaseModel):
    stall_name: str
    cuisine_type: str
    dishes: list[Dish]
    description: str = ""


@app.post("/api/generate-copy")
async def generate_copy(req: GenerateCopyRequest):
    if not GMI_API_KEY:
        raise HTTPException(status_code=500, detail="GMI_API_KEY not set")

    dish_list = "\n".join(
        f"- {d.name} ({d.price})" if d.price else f"- {d.name}" for d in req.dishes
    )
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
