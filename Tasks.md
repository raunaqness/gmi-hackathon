# HawkerBoost — Tasks

## Completed

- [x] **Project Scaffolding** — React (CDN) + Tailwind frontend, FastAPI backend, run.sh
- [x] **Image Parsing Pipeline** — Two-step: Gemini 3.1 Pro (vision) + GPT-5.4-mini (JSON structuring)
- [x] **Copy Generation Endpoint** — GLM-5.1 generates Instagram, Google Maps, WhatsApp copy in EN/ZH/BM
- [x] **Single-Page UI** — Upload photos, view cumulative stall profile, generate copy
- [x] **Multi-Image Upload** — Up to 5 photos at once, processed in parallel
- [x] **Smart Image Classification** — AI classifies each image as menu/stall/food/other
- [x] **Cumulative Stall Profile** — Each upload merges data (doesn't replace)
- [x] **Portion Size Parsing** — "$12/15/20" parsed as Small/Medium/Large with editable pills
- [x] **Singapore Dietary Tags** — Halal, No Pork No Lard, MUIS, Vegetarian, etc.
- [x] **Michelin Recognition** — Detects Michelin Star, Bib Gourmand, Michelin Selected
- [x] **Results Screen** — Language switcher (EN/ZH/BM), copy-to-clipboard per card, char counts
- [x] **Logging** — Backend logs to hawkerboost.log with full request/response tracing
- [x] **Polish** — Inter font, PRD colour palette, mobile-first layout

## Remaining

- [ ] Test full end-to-end flow with live GMI API on mobile browser
- [ ] Demo rehearsal with prepared test images
- [ ] Backup cached JSON response for demo fallback (file exists, not wired into frontend)
