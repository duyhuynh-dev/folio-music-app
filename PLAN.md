# Folio — Build Plan

Travel photos → AI scene reading → Apple Music suggestions.
Web-first (Next.js + Python/FastAPI). Reference: `folio_brief.pdf`.

---

## Phase 1 — Weeks 1–2: AI Pipeline Only

**Gate to exit:** 4 out of 5 manual photo tests feel genuinely right. No frontend, no FastAPI until this passes.

- [x] **1.1 — Project scaffold**
  - Create `backend/` with `pipeline/`, `services/`, `tests/`, `requirements.txt`, `.env.example`
  - CLI runner `run.py` (takes a photo path)
  - Secrets: `ANTHROPIC_API_KEY`, Last.fm API key
- [x] **1.2 — `pipeline/scene.py` (vision extraction)**
  - Claude Sonnet 4.6 vision → scene JSON (10-field schema from brief)
  - Pydantic model for validation
  - Tune prompt on 5 test photos
- [x] **1.3 — `pipeline/translate.py` (scene → music params)**
  - Claude text call → `search_queries`, `lastfm_tags`, `seed_artists`, `avoid`, `tempo`
- [x] **1.4 — `services/apple_music.py` + `services/lastfm.py` + `pipeline/fetch.py`**
  - Apple Music JWT (python-jose + `.p8`)
  - Parallel fetch, dedupe, cap at 10 candidates
- [x] **1.5 — `pipeline/rank.py`**
  - Claude re-ranks 10 → best 4 with one-line reason
  - Include `variation_seed` param (risk mitigation from brief)
- [ ] **1.6 — Eval harness (THE GATE)**
  - Harness script implemented in `backend/eval.py` (`generate` + `summarize`)
  - Run pipeline on 20 personal travel photos
  - Markdown report: photo + 4 picks + reasons
  - Score 1–5. Do not proceed until ≥80% feel right.

---

## Phase 2 — Weeks 3–5: FastAPI + Next.js MVP

**Gate to exit:** internal tester uploads photo → authorises Apple Music → gets 4 playable suggestions saved to account.

- [x] **2.1 — FastAPI wrapper:** `/api/suggest-music` + `/api/token` + `/health`, CORS, error handling
- [x] **2.2 — Supabase:** migration with `profiles`, `trips`, `moments`, `suggestions` + RLS + storage bucket
- [x] **2.3 — Next.js scaffold:** App Router, Tailwind, `lib/api.ts`, `lib/musickit.ts`
- [x] **2.4 — MusicKit auth flow:** developer JWT endpoint, MusicKit JS load, in-memory `music-user-token`
- [x] **2.5 — Upload screen:** drag-drop, EXIF extraction stub, loading state
- [x] **2.6 — MusicPicker component:** 4 cards, 30s preview player, one-line reason, "Try different vibe", "Use this one"
- [ ] **2.7 — Internal testing:** 3–5 people × 10 photos, track failure modes

---

## Phase 3 — Weeks 6–10: Map + Sharing + First 50 Beta Users

**Gate to exit:** 50 beta users, ≥10 shared public trip pages.

- [x] **3.1 — Trip memory map** (`components/TripMap.tsx`): Mapbox GL JS, pins per moment, tap = photo + song + reason popup
- [x] **3.2 — Replay mode** (`ReplayPlayer.tsx`): animate route chronologically, autoplay songs in sequence
- [x] **3.3 — Shareable trip page:** `/trip/[id]` with map, replay, "Make your own" CTA
- [x] **3.4 — Non-subscriber support:** MusicKit auth is optional, 30s previews work without subscription
- [x] **3.5 — Trip management:** backend endpoints for create trip + add moment, TripManager component
- [ ] **3.6 — Beta launch:** Reddit (r/solotravel, r/travel, r/roadtrip), feedback form, Posthog analytics

---

## Phase 4 — Weeks 11–16: Video Export, Rewind, Taste Learning

**Gate to exit:** video export works, annual rewind page live, taste signals logging.

- [ ] **4.1 — Video export:** server-side ffmpeg on Railway — map animation + photos + synced audio
- [ ] **4.2 — Annual Rewind:** December feature stitching year's trips into one map + playlist
- [ ] **4.3 — Taste learning:** log accept/reject per suggestion, feed Stage 4 ranking as personalisation signal

> **Mobile (React Native + Expo):** deferred until web version is fully working and proven.

---

## Phase 5 — Weeks 17+: Print, Personalisation, B2B

No fixed deadline — pursue based on Phase 4 traction.

- [ ] **5.1 — Printed Memory Book:** Gelato API, auto-layout A5 booklet (map, playlist QR, photos, members, dates), $18–28 one-time
- [ ] **5.2 — Feedback loop:** dataset of `{scene_json → chosen_track}` — proprietary asset. Use to few-shot Stage 2/4 prompts
- [ ] **5.3 — Apple Music + Last.fm personalisation:** pull listening history (with consent), bias seed_artists toward user taste
- [ ] **5.4 — B2B Brand Trips:** sponsored curated playlists ("Iceland by Icelandair"), pitch deck + outreach
- [ ] **5.5 — Acquisition prep:** data room (metrics, dataset size, cohort retention) for Spotify/Apple/Airbnb/Polarsteps

---

## Monetisation (current)

- Printed Memory Book ($18–28 one-time, zero inventory via Gelato)
- B2B Brand Trips (Phase 5+)
- All features are free to all users (no premium subscription tier)

## Key Risks (from brief)

- Apple Music API stability → Last.fm as fallback from Phase 2
- AI suggestion quality → Phase 1 gate is non-negotiable
- "Try different vibe" must actually differ → `variation_seed` in Stage 4
- Background GPS drains battery → low-accuracy mode only (Phase 4)
