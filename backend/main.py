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


# --- Task 2: Menu Photo Parsing ---

class ParseMenuRequest(BaseModel):
    image_base64: str


@app.post("/api/parse-menu")
async def parse_menu(req: ParseMenuRequest):
    if not GMI_API_KEY:
        raise HTTPException(status_code=500, detail="GMI_API_KEY not set")

    payload = {
        "model": "gpt-4o-mini",
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
                            "You are extracting structured data from a food menu photo.\n"
                            "Return a JSON object with:\n"
                            '- "stall_name": the name of the stall if visible, else null\n'
                            '- "cuisine_type": inferred cuisine type (e.g. "Chinese", "Malay", "Indian", "Western")\n'
                            '- "dishes": an array of objects with "name" (string) and "price" (string, e.g. "$3.50")\n\n'
                            "Only return valid JSON. No explanation."
                        ),
                    },
                ],
            }
        ],
        "max_tokens": 1000,
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
        # Strip markdown code fences if present
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        parsed = json.loads(content)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=502, detail=f"Failed to parse API response: {e}")

    return parsed
