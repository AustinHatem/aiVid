# aiVid — Automated Short-Form Video Ad Generator

Automated pipeline for generating TikTok-style video ads for **Someone Somewhere** (a video chat dating app). Multiple pipeline versions produce 9-15 second portrait videos combining AI-generated video, text overlays, voiceovers, captions, and music.

## Pipelines at a Glance

| Version | Script | Duration | What It Does | APIs Needed |
|---------|--------|----------|-------------|-------------|
| **V2** | `generate_v2.py` | ~15s | English ads — woman speaks hook, reacts, screen recording | Kling, GPT-4o, ElevenLabs, Whisper |
| **V3** | `generate_v3.py` | ~15s | Spanish (LATAM) version of V2, empowering tone | Kling, GPT-4o, ElevenLabs, Whisper |
| **V4** | `generate_v4.py` | 9s | Lightweight — stitches existing videos + text overlay, no AI | FFmpeg + Pillow only |
| **V5** | `generate_v5.py` | 13s | Complex 4-segment with captions, music, PiP | GPT-4o, ElevenLabs, Whisper |
| **Surprised** | `generate_surprised.py` | 5s | Generates reaction videos from photos via Kling | Kling 3.0/2.6/2.1 |

## Setup

### Environment Variables

Create a `.env` file in the project root:

```
OPENAI_API_KEY=sk-proj-...
ELEVENLABS_API_KEY=sk_...
```

### Firebase Service Account

Place your Firebase service account JSON in the project root. It's auto-discovered by glob pattern: `*-firebase-adminsdk-*.json`

- **Project:** `somesome-a6df1`
- **Storage bucket:** `gs://somesome-a6df1.firebasestorage.app`
- If the JSON is missing, scripts still work — they just skip Firebase upload and Google Sheets logging.

### Google Sheets

Sheet ID: `1h1pPMEshYzfCyqA-xc4NHVcGotQk_-S_LzfFhPaPlhQ`

Each pipeline writes to its own worksheet tab: "V2 Ads", "V3 Ads" (called "Latam Female Ads"), "V4 Ads", "V5 Ads". Tabs are auto-created on first run.

### Python Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install python-dotenv openai elevenlabs firebase-admin gspread pillow requests higgsfield-client
```

### System Dependencies

- **FFmpeg** with libx264 (install via `brew install ffmpeg`)
- **macOS** for Apple Color Emoji font (used in V2/V3 title rendering)

## Running

### Single run

```bash
source .venv/bin/activate
python generate_v2.py              # 1 English ad
python generate_v3.py              # 1 Spanish ad
python generate_v4.py              # 10 lightweight ads (batch)
python generate_v5.py              # 1 complex ad
python generate_surprised.py       # Generate reaction videos from all photos in femalePhotos_v5/
```

### Batch runs

```bash
./run_v3_x6.sh     # 10 sequential V3 runs
./run_v5_x20.sh    # 20 sequential V5 runs
```

### Passing a specific photo (V2/V3)

```bash
python generate_v2.py photo_14    # Use specific image by basename
```

## Directory Structure

```
fonts/                   TTF/OTF fonts (TikTokSans, DMSans, Montserrat, Roboto, BebasNeue)
songs/                   Background music MP3s (7 tracks)
screenRecording/         App screen recordings for V2/V3/V5
  screenSwiping/         Swiping demo clips for V5 segment 2

femalePhotosV2/          V2 input photos (JPEG)
femalePhotosV3/          V3 input photos (Latina JPGs)
femalePhotos_v5/         High-res PNGs for Surprised pipeline
femaleSuprised/          Output from Surprised pipeline (part1/part2/surprised MP4s, used by V5)

girlsChat/               Female reaction videos (used as PiP in V4, fullscreen in V4)
guysChat/                Male reaction videos (used as PiP/fullscreen in V4)

ssUI.png                 App UI overlay (V2, V3, V5) — 1080x1920 RGBA
ssUI2.png                App UI overlay (V4) — 1080x1611 RGBA

output/                  Generated videos from V2/V3/V4
output_v5/               Generated videos from V5
```

## Pipeline Details

### V2 — English Ads (`generate_v2.py`)

**Video structure:**
- 0-5s: Woman speaks the hook (Kling 3.0 talking video)
- 5-8.5s: Screen recording with ssUI overlay
- 8.5-11.5s: Woman reacts/laughs with ssUI overlay
- 11.5-15s: Second screen recording

**Audio layers:** Talk audio (0-5s) + background song (full, 8% vol) + voiceover (starts at 5s, 1.8x vol) + Whisper-synced captions

**GPT tone:** Edgy, flirty, Gen Z, thirst-trap energy. Must mention "Someone Somewhere" by name.

**Kling models:** Tries v3.0 first, falls back to v2.1 if NSFW-flagged.

### V3 — Spanish LATAM Ads (`generate_v3.py`)

Fork of V2 with these changes:
- All GPT prompts output Colombian/LATAM Spanish (not Spain Spanish — no "tio", "mola", "vale")
- Tone: warm, empowering, girl-power (not edgy/flirty)
- Photos from `femalePhotosV3/`
- ElevenLabs `eleven_multilingual_v2` handles Spanish natively with the same voice IDs
- Logs to "Latam Female Ads" worksheet

### V4 — Lightweight Screen Ads (`generate_v4.py`)

**No AI generation at all.** Pure FFmpeg composition. Generates 10 videos per run.

**Video structure (3 segments, 3s each = 9s total):**
- Seg 1: Girl video fullscreen + ssUI2 overlay + guy PiP (top-right) + text overlay
- Seg 2: Guy video fullscreen + ssUI2 overlay + girl PiP (top-right) + text overlay (swapped)
- Seg 3: Girl video fullscreen + ssUI2 overlay + guy PiP (top-right) + text overlay

**Text overlay:** 30 hardcoded ad texts, randomly selected per video. Rendered with TikTok Sans Variable Font (SemiBold, weight 600). White text with 5px black outline.

**PiP features:** 270px wide, 30px rounded corners (4x oversampled for smooth anti-aliasing), drop shadow with Gaussian blur.

**No audio** in current version.

### V5 — Complex 4-Segment Ads (`generate_v5.py`)

**Video structure (4 segments, 13s total):**
- Seg 1 (0-3s): Girl part1 + GPT hook text overlay
- Seg 2 (3-8.5s): Screen swiping demo (1.5x speed)
- Seg 3 (8.5-11s): Screen recording (camera/call UI)
- Seg 4 (11-13s): Girl part2 + ssUI overlay + guy PiP (rounded corners)

**Audio:** Song (8% vol) + voiceover (delayed 3s, 1.8x vol) + Whisper captions as ASS subtitles

**Inputs from Surprised pipeline:** Uses `femaleSuprised/*_part1.mp4` and `*_part2.mp4` files.

### Surprised — Reaction Video Generator (`generate_surprised.py`)

Takes high-res photos from `femalePhotos_v5/` and generates 5s reaction videos using Kling image-to-video.

**NSFW fallback chain:** Kling 3.0 -> 2.6 -> 2.1. If one model flags the image, it automatically tries the next.

**Outputs:** `femaleSuprised/{basename}_surprised.mp4` plus split `_part1.mp4` and `_part2.mp4` for V5 consumption.

## ElevenLabs Voice IDs

Three female voices, randomly selected per run:

```
21m00Tcm4TlvDq8ikWAM  — Rachel (warm, calm)
EXAVITQu4vr4xnSDxMaL  — Bella (soft, friendly)
MF3mGyEYCl7XYWbV9V6O  — Elli (young, cheerful)
```

## Output Specs

- **Resolution:** 1080x1920 (9:16 portrait)
- **Codec:** H.264 (libx264), CRF 18
- **Frame rate:** 30 fps
- **Audio:** AAC 128kbps (V2/V3/V5) or none (V4)

## Gotchas and Tips

### Variable font axis ordering is critical (V4/V5)

The TikTok variable font axes must be set in exact order: `opsz, wdth, wght, slnt`. Getting this wrong silently applies values to the wrong axes (e.g., your "bold" setting goes to slant instead).

```python
# CORRECT axis order
font.set_variation_by_axes([36, 100, 600, 0])  # opsz=36, wdth=100, wght=600, slnt=0

# WRONG — will produce unexpected results
font.set_variation_by_axes([36, 0, 100, 600])  # slnt and wdth swapped with wght
```

### Variable fonts break ASS subtitles (V2/V3/V5)

Variable font filenames contain commas (e.g., `TikTokSans-VariableFont_opsz,slnt,wdth,wght.ttf`). The ASS subtitle format chokes on commas in font paths. All caption pipelines explicitly filter these out:

```python
files = [f for f in os.listdir(FONTS_DIR) if "VariableFont" not in f]
```

### Voiceover speed-up logic

If ElevenLabs generates audio longer than the max duration, it's automatically sped up using FFmpeg's `atempo` filter (preserves pitch). The speedup factor is capped — if it would need more than ~1.5x, the script warns but still applies it.

### Kling NSFW fallback

Kling models sometimes flag images as NSFW even when they aren't. The codebase handles this by trying models in order: 3.0 -> 2.6 -> 2.1. Only raises an error if ALL models fail.

### PiP rounded corners need oversampling

The PiP mask is generated at 4x resolution then downscaled with Lanczos resampling. Without this, rounded corners appear pixelated. Don't skip the oversampling step.

### Firebase is optional

All scripts check for the Firebase service account JSON at startup. If missing, they print a warning and skip upload/logging. Videos are still generated locally in `output/` or `output_v5/`.

### System Python vs venv

macOS Homebrew Python is "externally managed" and blocks `pip install`. Either use the venv (`.venv/`) or pass `--break-system-packages` to pip. The venv approach is recommended since all deps are already installed there.

### FFmpeg filter chain complexity (V5)

V5's single-pass FFmpeg command has 11 inputs and a massive `-filter_complex` chain. If you need to debug, add `-t 3` to the FFmpeg command to test with just the first 3 seconds. Check `stderr` output — FFmpeg prints detailed error messages about which filter failed.

### Google Sheets rate limits

When generating many videos in sequence (batch scripts), Google Sheets API can throw 500 errors. The current code doesn't retry — it crashes. If this happens, just rerun. The videos already uploaded to Firebase are fine.

### Title rendering with emoji (V2/V3)

Emoji are split from the text and rendered separately using the system Apple Color Emoji font. This only works on macOS. The emoji are composited onto the title image at the correct position.
