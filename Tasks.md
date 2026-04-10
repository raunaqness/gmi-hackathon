# HawkerBoost — Build Tasks

## Task 1: Project Scaffolding
- [x] Init React (CDN) with Tailwind CSS
- [x] Init FastAPI backend with project structure
- [x] Verify both dev servers run

## Task 2: Backend — Menu Photo Parsing Endpoint
- [x] `POST /api/parse-menu` — accepts base64 image, calls GMI Image API
- [x] Returns `{ stall_name, cuisine_type, dishes: [{ name, price }] }`
- [x] Error handling for bad images / API failures

## Task 3: Backend — Copy Generation Endpoint
- [x] `POST /api/generate-copy` — accepts stall info + dishes, calls GLM-5.1
- [x] Returns `{ en: { instagram, google_maps, whatsapp }, zh: {...}, bm: {...} }`
- [x] Error handling for API failures / malformed responses

## Task 4: Frontend — Landing Page
- [x] Logo + tagline
- [x] Two CTA buttons: Upload Menu Photo / Enter Manually
- [x] 3-icon explainer (Snap > Generate > Copy)
- [x] Mobile-first layout, colour palette from PRD

## Task 5: Frontend — Photo Upload + Confirm Screen
- [x] Image upload component (JPG/PNG/HEIC)
- [x] Call `/api/parse-menu`, show loading state
- [x] Display editable dish table from parsed results
- [x] Stall name + cuisine type fields
- [x] "Generate Copy" CTA

## Task 6: Frontend — Manual Entry Form
- [x] Stall name (required), cuisine type (dropdown), stall description (optional)
- [x] Dynamic dish table (name + price rows) with Add/Remove
- [x] Validation: at least 1 dish required
- [x] "Generate Copy" CTA

## Task 7: Frontend — Results Screen
- [x] Language switcher pill tabs (EN / ZH / BM)
- [x] Three cards: Instagram, Google Maps, WhatsApp
- [x] Copy-to-clipboard button per card with "Copied" feedback
- [x] Character count per output block
- [x] "Start Over" link

## Task 8: Integration + Loading States
- [x] Wire frontend to backend API calls
- [x] Two-phase loading overlay (reading menu / writing captions)
- [x] Error state handling (API timeout, bad image, etc.)

## Task 9: Polish + Mobile Styling
- [x] Responsive layout (max-w-md, mobile-first)
- [x] Colour palette, Inter font, card design
- [x] Transitions (active:scale-95 on buttons)

## Task 10: Testing + Demo Prep
- [x] Prepare backup cached JSON response
- [ ] Test with real GMI API key (requires `GMI_API_KEY` env var)
- [ ] Test full end-to-end flow on mobile browser
