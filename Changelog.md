# HawkerBoost — Changelog

## 2026-04-10

### `cdad610` fix: use max_completion_tokens for GPT-5.4-mini
- GPT-5.4 models require `max_completion_tokens` instead of legacy `max_tokens`

### `bf57c99` feat: two-step pipeline — Gemini for vision, GPT-5.4-mini for JSON
- Replaced single Gemini call (which often returned invalid JSON) with two-step pipeline
- Step 1: Gemini 3.1 Pro analyzes image in free-form text (no JSON requirement)
- Step 2: GPT-5.4-mini converts description into clean structured JSON (temperature=0)
- Removed retry logic — no longer needed with this approach

### `9f28c9a` feat: add retry logic (3 attempts) and log to file
- Added structured logging throughout backend (hawkerboost logger)
- Backend logs to `hawkerboost.log` with full request/response tracing
- run.sh prints log path and tail command on startup
- *(Retries later removed in favor of two-step pipeline)*

### `0a7f074` feat: multi-image upload, up to 5 photos at once
- File input accepts multiple files, processes in parallel
- Upload button shows count (0/5), disables at limit
- Pending counter tracks all in-flight requests before clearing uploading state

### `eb2215c` feat: smart price parsing, dietary/Michelin tags, portion sizes
- Gemini prompt understands "$12/15/20" as Small/Medium/Large portion sizes
- Extracts Singapore dietary tags: Halal, No Pork No Lard, MUIS, Vegetarian
- Detects Michelin Bib Gourmand/Star/Selected logos
- Frontend shows portion sizes as editable orange pills
- Tags shown as color-coded badges (green=Halal, red=Michelin, purple=other)

### `2c29363` feat: redesign to single-page with multi-photo upload and cumulative profile
- Replaced multi-screen flow with single-page layout
- New `/api/parse-image` endpoint replaces `/api/parse-menu`
- AI classifies images as menu/stall/food/other with badge display
- Cumulative stall profile: each upload merges into existing data
- Editable stall details card + menu items card
- "Generate Marketing Copy" button appears when enough info present

### `1f4b9ae` chore: add backup demo response and update task status
- Cached sample API response in `frontend/backup-response.json`

### `d4ac48b` polish: add Inter font and improve styling
- Google Inter font, CSS animation keyframes, font smoothing

### `f6773aa` feat: build complete frontend
- All screens: landing, photo upload/confirm, manual entry, results
- Language switcher (EN/ZH/BM), copy-to-clipboard, char counts

### `8e4fe40` feat: add /api/generate-copy endpoint
- GLM-5.1 generates Instagram, Google Maps, WhatsApp copy in 3 languages

### `0a6f224` feat: add /api/parse-menu endpoint
- GMI Image API (gpt-4o-mini) for menu photo OCR

### `59df62d` scaffold: init project
- React via CDN + Tailwind CSS frontend
- FastAPI backend with CORS
- run.sh to start both servers
