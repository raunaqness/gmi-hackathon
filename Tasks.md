# HawkerBoost — Build Tasks

## Task 1: Project Scaffolding
- [ ] Init React app (Vite) with Tailwind CSS
- [ ] Init FastAPI backend with project structure
- [ ] Verify both dev servers run

## Task 2: Backend — Menu Photo Parsing Endpoint
- [ ] `POST /api/parse-menu` — accepts base64 image, calls GMI Image API
- [ ] Returns `{ stall_name, cuisine_type, dishes: [{ name, price }] }`
- [ ] Error handling for bad images / API failures

## Task 3: Backend — Copy Generation Endpoint
- [ ] `POST /api/generate-copy` — accepts stall info + dishes, calls GLM-5.1
- [ ] Returns `{ en: { instagram, google_maps, whatsapp }, zh: {...}, bm: {...} }`
- [ ] Error handling for API failures / malformed responses

## Task 4: Frontend — Landing Page
- [ ] Logo + tagline
- [ ] Two CTA buttons: Upload Menu Photo / Enter Manually
- [ ] 3-icon explainer (Snap > Generate > Copy)
- [ ] Mobile-first layout, colour palette from PRD

## Task 5: Frontend — Photo Upload + Confirm Screen
- [ ] Image upload component (JPG/PNG/HEIC)
- [ ] Call `/api/parse-menu`, show loading state
- [ ] Display editable dish table from parsed results
- [ ] Stall name + cuisine type fields
- [ ] "Generate Copy" CTA

## Task 6: Frontend — Manual Entry Form
- [ ] Stall name (required), cuisine type (dropdown), stall description (optional)
- [ ] Dynamic dish table (name + price rows) with Add/Remove
- [ ] Validation: at least 1 dish required
- [ ] "Generate Copy" CTA

## Task 7: Frontend — Results Screen
- [ ] Language switcher pill tabs (EN / ZH / BM)
- [ ] Three cards: Instagram, Google Maps, WhatsApp
- [ ] Copy-to-clipboard button per card with "Copied" feedback
- [ ] Character count per output block
- [ ] "Start Over" link

## Task 8: Integration + Loading States
- [ ] Wire frontend to backend API calls
- [ ] Two-phase loading overlay (reading menu / writing captions)
- [ ] Error state handling (API timeout, bad image, etc.)

## Task 9: Polish + Mobile Styling
- [ ] Responsive layout tested at 390px
- [ ] Colour palette, typography, card design
- [ ] Smooth transitions and animations
- [ ] Final UI polish pass

## Task 10: Testing + Demo Prep
- [ ] Test with multiple menu photos
- [ ] Test manual entry flow
- [ ] Test all language tabs + copy buttons
- [ ] Prepare backup cached JSON response
- [ ] Verify full end-to-end flow
