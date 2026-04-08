from dotenv import load_dotenv
load_dotenv()

import higgsfield_client
import requests
import subprocess
import os
import sys
import random
import glob
from datetime import datetime
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
import firebase_admin
from firebase_admin import credentials, storage
import gspread
from elevenlabs.client import ElevenLabs

# --- Config ---
# Video 1: Kling 3.0 — speaking the hook (native audio)
TALK_MODEL = "kling-video/v3.0/pro/image-to-video"
# Video 2: Kling 2.1 — silent reaction clip (smiling/warm)
REACT_MODEL = "kling-video/v2.1/pro/image-to-video"
PHOTOS_DIR = "femalePhotosV3"
SCREEN_REC_DIR = "screenRecording"
SONGS_DIR = "songs"
FONTS_DIR = "fonts"
OUTPUT_DIR = "output"
UI_OVERLAY = "ssUI.png"
GSHEET_ID = "1h1pPMEshYzfCyqA-xc4NHVcGotQk_-S_LzfFhPaPlhQ"

# Firebase + Google Sheets setup
_sa_files = glob.glob("*-firebase-adminsdk-*.json")
if _sa_files:
    _cred = credentials.Certificate(_sa_files[0])
    firebase_admin.initialize_app(_cred, {"storageBucket": "somesome-a6df1.firebasestorage.app"})
    _gc = gspread.service_account(filename=_sa_files[0])
else:
    _gc = None
    print("WARNING: No Firebase service account JSON found — uploads/logging will be skipped.")

# ElevenLabs TTS setup
elevenlabs = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
# Female voices — eleven_multilingual_v2 model handles Spanish natively
ELEVEN_VOICES = [
    "21m00Tcm4TlvDq8ikWAM",  # Rachel — warm, calm
    "EXAVITQu4vr4xnSDxMaL",  # Bella — soft, friendly
    "MF3mGyEYCl7XYWbV9V6O",  # Elli — young, cheerful
]

# Example voiceover scripts in Spanish (~5 seconds each) to teach GPT the style
EXAMPLE_VOICEOVERS = [
    "Someone Somewhere conecta mujeres increíbles con personas reales. Tú mereces esto.",
    "Deja de esperar y empieza a vivir. Someone Somewhere tiene gente increíble esperándote.",
    "Someone Somewhere es donde las mujeres seguras conocen a personas que valen la pena.",
    "Conversaciones reales con gente real. Someone Somewhere te está esperando, atrévete.",
]

# Example hooks in Spanish — empowering, warm, confident
EXAMPLE_HOOKS = [
    "Mereces conocer a alguien increíble en Someone Somewhere",
    "Someone Somewhere me cambió la vida por completo",
    "Yo encontré mi persona favorita en Someone Somewhere",
    "No sigas esperando, tu persona está en Someone Somewhere",
    "Someone Somewhere tiene la mejor vibra del mundo",
    "Atrévete a conocer gente real en Someone Somewhere",
    "Las mejores conversaciones están en Someone Somewhere",
    "Someone Somewhere es para mujeres que saben lo que quieren",
    "Mi mejor descubrimiento del año fue Someone Somewhere",
    "Conecta con personas increíbles en Someone Somewhere",
]

os.makedirs(OUTPUT_DIR, exist_ok=True)

openai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def generate_hook() -> str:
    """Use GPT to generate a short, punchy Spanish ad hook for Someone Somewhere."""
    print("[1/4] Generating Spanish ad hook (~5s)...")
    examples_block = "\n".join(f"- {h}" for h in EXAMPLE_HOOKS)
    resp = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You write viral short-form video ad hooks IN SPANISH for the Someone Somewhere app — "
                    "a video chat app where you meet and talk to real, attractive people worldwide.\n\n"
                    "IMPORTANT: All output must be in natural, conversational Latin American Spanish "
                    "(Colombian/LATAM dialect — avoid Spain-specific vocabulary like 'tío', 'mola', 'vale').\n\n"
                    "Rules:\n"
                    "- The hook is spoken directly to camera by a confident, warm Latina woman.\n"
                    "- ONE sentence, under 12 words IN SPANISH, takes ~5 seconds to say.\n"
                    "- Tone: Friendly, empowering, confident — girl-power energy.\n"
                    "- Think: warm invitation, you deserve this, meet amazing people, live your best life.\n"
                    "- NOT edgy, flirty, or suggestive. Instead: uplifting, aspirational, welcoming.\n"
                    "- Must mention 'Someone Somewhere' by name (keep in English — it's the app name).\n"
                    "- Place 'Someone Somewhere' where it flows naturally in the Spanish sentence.\n"
                    "- Create a sense of excitement, empowerment, or a personal invitation.\n"
                    "- Keep it PG — inspiring, not suggestive.\n"
                    "- Do NOT repeat the examples — come up with something fresh.\n"
                    "- Do NOT use hashtags, emojis, or quotation marks.\n"
                    "- Return ONLY the raw Spanish sentence, nothing else.\n\n"
                    f"Here are example hooks for reference:\n{examples_block}"
                ),
            },
            {
                "role": "user",
                "content": "Write a new, unique ~5-second spoken ad hook IN SPANISH for Someone Somewhere.",
            },
        ],
        temperature=1.1,
        max_tokens=60,
    )
    hook = resp.choices[0].message.content.strip().strip('"').strip("'")
    print(f"      Hook: \"{hook}\"")
    return hook


def generate_voiceover_script() -> str:
    """Use GPT to generate a ~5-second Spanish voiceover script for Someone Somewhere."""
    print("[VO] Generating Spanish voiceover script...")
    examples_block = "\n".join(f"- {v}" for v in EXAMPLE_VOICEOVERS)
    resp = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You write voiceover scripts IN SPANISH for short-form video ads for the Someone Somewhere app — "
                    "a video chat app where you meet and talk to real, attractive people worldwide.\n\n"
                    "IMPORTANT: All output must be in natural, conversational Latin American Spanish "
                    "(Colombian/LATAM dialect).\n\n"
                    "Rules:\n"
                    "- The voiceover is read by a warm, confident young Latina narrator.\n"
                    "- It must be 1-2 SHORT sentences, MAX 14 words total IN SPANISH.\n"
                    "- It should take about 4-5 seconds to say at a natural pace. Keep it SHORT.\n"
                    "- Tone: Empowering, friendly, girl-power energy — like your best friend hyping you up.\n"
                    "- NOT edgy, flirty, or provocative. Instead: warm, encouraging, uplifting.\n"
                    "- Must mention 'Someone Somewhere' by name at least once (keep in English).\n"
                    "- Create excitement — make it sound like an amazing experience awaits them.\n"
                    "- Highlight: real people, genuine connections, video chat, confidence, self-worth.\n"
                    "- Do NOT repeat the examples — come up with something fresh and original.\n"
                    "- Do NOT use hashtags, emojis, or quotation marks.\n"
                    "- Return ONLY the raw Spanish voiceover text, nothing else.\n\n"
                    f"Here are example voiceovers for reference:\n{examples_block}"
                ),
            },
            {
                "role": "user",
                "content": "Write a new, unique ~5-second voiceover script IN SPANISH for a Someone Somewhere ad.",
            },
        ],
        temperature=1.1,
        max_tokens=80,
    )
    script = resp.choices[0].message.content.strip().strip('"').strip("'")
    print(f"      Script: \"{script}\"")
    return script


def generate_voiceover_audio(script: str, output_path: str, max_duration: float = 5.0) -> str:
    """Use ElevenLabs TTS to generate a female Spanish voiceover audio file.
    If the audio exceeds max_duration, speed it up with ffmpeg to fit."""
    voice_id = random.choice(ELEVEN_VOICES)
    print(f"[VO] Generating TTS audio (ElevenLabs voice: {voice_id})...")
    audio = elevenlabs.text_to_speech.convert(
        voice_id=voice_id,
        text=script,
        model_id="eleven_multilingual_v2",
    )
    raw_path = output_path + ".raw.mp3"
    with open(raw_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)

    # Check duration
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", raw_path],
        capture_output=True, text=True
    )
    duration = float(probe.stdout.strip())
    print(f"      TTS duration: {duration:.1f}s (max: {max_duration}s)")

    if duration > max_duration:
        # Speed up audio to fit within max_duration
        speed = duration / max_duration
        print(f"      Speeding up by {speed:.2f}x to fit...")
        subprocess.run(
            ["ffmpeg", "-y", "-i", raw_path, "-filter:a", f"atempo={speed}",
             "-c:a", "libmp3lame", "-q:a", "2", output_path],
            capture_output=True, text=True, timeout=30
        )
        os.remove(raw_path)
        duration = max_duration
    else:
        os.rename(raw_path, output_path)

    print(f"      Voiceover saved: {output_path} ({duration:.1f}s)")
    return output_path


def transcribe_audio(audio_path: str) -> list:
    """Use Whisper to get word-level timestamps from an audio file."""
    print(f"[CAP] Transcribing {audio_path} for captions...")
    with open(audio_path, "rb") as f:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json",
            timestamp_granularities=["word"],
        )
    words = [{"word": w.word, "start": w.start, "end": w.end} for w in transcript.words]
    print(f"      Got {len(words)} words with timestamps")
    return words


def pick_font() -> str:
    """Pick a random font from the fonts directory."""
    files = sorted(
        f for f in os.listdir(FONTS_DIR)
        if f.lower().endswith((".ttf", ".otf"))
        # Exclude variable fonts — commas in filename break ASS subtitle format
        and "VariableFont" not in f
    )
    if not files:
        raise FileNotFoundError(f"No fonts found in {FONTS_DIR}/")
    picked = random.choice(files)
    path = os.path.join(FONTS_DIR, picked)
    print(f"      Font: {picked}")
    return path


# TikTok-style title color schemes: (bg_hex, text_hex)
TITLE_COLORS = [
    ("#FFFFFF", "#000000"),  # white bg, black text
    ("#000000", "#FFFFFF"),  # black bg, white text
    ("#d72b3b", "#FFFFFF"),  # TikTok red bg, white text
]

# Example titles in Spanish — empowering, warm
EXAMPLE_TITLES = [
    "mereces algo mejor 💅",
    "tu persona te está esperando 🫶",
    "abre Someone Somewhere ya 🔥",
    "conecta con gente real 💜",
    "esto te va a encantar 😍",
    "la app que necesitabas 🤭",
]


def generate_title() -> str:
    """Use GPT to generate a short TikTok-style Spanish title with emoji."""
    print("[TITLE] Generating Spanish title...")
    examples_block = "\n".join(f"- {t}" for t in EXAMPLE_TITLES)
    resp = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You write short TikTok-style title overlays IN SPANISH for viral video ads "
                    "targeting young Latina women.\n\n"
                    "Rules:\n"
                    "- MAX 5-6 words total IN SPANISH.\n"
                    "- Must include 1 emoji at the end.\n"
                    "- Warm, empowering, confident — girl-power energy.\n"
                    "- NOT edgy or suggestive. Uplifting and inviting instead.\n"
                    "- All lowercase or mixed case (not ALL CAPS).\n"
                    "- Do NOT repeat the examples — come up with something fresh.\n"
                    "- Do NOT use hashtags or quotation marks.\n"
                    "- Return ONLY the raw Spanish title, nothing else.\n\n"
                    f"Example titles:\n{examples_block}"
                ),
            },
            {
                "role": "user",
                "content": "Write a new, unique TikTok-style title overlay IN SPANISH for a video chat app ad.",
            },
        ],
        temperature=1.2,
        max_tokens=30,
    )
    title = resp.choices[0].message.content.strip().strip('"').strip("'")
    print(f"      Title: \"{title}\"")
    return title


def _split_emoji(text: str) -> list:
    """Split text into runs of (is_emoji, substring)."""
    import re
    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF"
        "\U00002600-\U000026FF\U0000FE0F\U0000200D]+"
    )
    parts = []
    last = 0
    for m in emoji_pattern.finditer(text):
        if m.start() > last:
            parts.append((False, text[last:m.start()]))
        parts.append((True, m.group()))
        last = m.end()
    if last < len(text):
        parts.append((False, text[last:]))
    return parts


def render_title_image(title: str, font_path: str, output_path: str) -> str:
    """
    Render a TikTok-style title as a transparent PNG overlay.
    Each line gets its own tight rounded-corner background box.
    Uses TikTokSans-Bold for text, Apple Color Emoji for emoji.
    """
    bg_hex, text_hex = random.choice(TITLE_COLORS)
    print(f"[TITLE] Rendering title image (bg={bg_hex}, text={text_hex})")

    img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    tiktok_font_path = os.path.join(FONTS_DIR, "TikTokSans-Bold.ttf")
    font_size = 48
    try:
        text_font = ImageFont.truetype(tiktok_font_path, font_size)
    except Exception:
        text_font = ImageFont.truetype(font_path, font_size)

    emoji_font = None
    emoji_font_path = "/System/Library/Fonts/Apple Color Emoji.ttc"
    if os.path.exists(emoji_font_path):
        try:
            emoji_font = ImageFont.truetype(emoji_font_path, font_size)
        except Exception:
            pass

    parts = _split_emoji(title)
    text_only = "".join(s for is_emoji, s in parts if not is_emoji).strip()
    emoji_only = "".join(s for is_emoji, s in parts if is_emoji).strip()

    words = text_only.split()
    lines = []
    current_line = ""
    for word in words:
        test = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=text_font)
        if bbox[2] - bbox[0] > 700 and current_line:
            lines.append(current_line)
            current_line = word
        else:
            current_line = test
    if current_line:
        lines.append(current_line)

    bg_color = tuple(int(bg_hex.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)) + (240,)
    text_color = text_hex

    pad_x, pad_y = 40, 24
    gap = 0
    corner_radius = 12
    y_start = 260

    for i, line in enumerate(lines):
        is_last = (i == len(lines) - 1)
        emoji_w = 0
        if is_last and emoji_only and emoji_font:
            eb = draw.textbbox((0, 0), f" {emoji_only}", font=emoji_font)
            emoji_w = eb[2] - eb[0]

        bbox = draw.textbbox((0, 0), line, font=text_font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        box_w = text_w + emoji_w + pad_x * 2
        box_h = text_h + pad_y * 2
        box_x = (1080 - box_w) // 2
        box_y = y_start + i * (box_h + gap)

        draw.rounded_rectangle(
            [box_x, box_y, box_x + box_w, box_y + box_h],
            radius=corner_radius,
            fill=bg_color,
        )

        text_x = box_x + pad_x - bbox[0]
        text_y = box_y + pad_y - bbox[1]
        draw.text((text_x, text_y), line, fill=text_color, font=text_font)

        if is_last and emoji_only and emoji_font:
            emoji_x = text_x + text_w + bbox[0]
            draw.text(
                (emoji_x, text_y), f" {emoji_only}",
                font=emoji_font, embedded_color=True,
            )

    img.save(output_path, "PNG")
    print(f"      Title image: {output_path}")
    return output_path


def pick_subtitle_style() -> dict:
    """Pick a random subtitle style from 4 options."""
    styles = [
        {
            "name": "white_outline",
            "desc": "White text, black outline",
            "primary": "&H00FFFFFF",
            "outline_col": "&H00000000",
            "back": "&H80000000",
            "border_style": 1,
            "outline": 5,
            "shadow": 2,
            "bold": -1,
            "fontsize": 88,
        },
        {
            "name": "pink_box",
            "desc": "Dark text on pink/beige box",
            "primary": "&H00252525",
            "outline_col": "&H00C8D4E8",
            "back": "&H00C8D4E8",
            "border_style": 3,
            "outline": 22,
            "shadow": 0,
            "bold": -1,
            "fontsize": 80,
        },
        {
            "name": "blue_box",
            "desc": "White text on blue/purple box",
            "primary": "&H00FFFFFF",
            "outline_col": "&H00B04828",
            "back": "&H00B04828",
            "border_style": 3,
            "outline": 22,
            "shadow": 0,
            "bold": -1,
            "fontsize": 80,
        },
        {
            "name": "dark_box",
            "desc": "White text on dark box (70% opacity)",
            "primary": "&H00FFFFFF",
            "outline_col": "&H4D282828",
            "back": "&H4D282828",
            "border_style": 3,
            "outline": 22,
            "shadow": 0,
            "bold": -1,
            "fontsize": 80,
        },
    ]
    return random.choice(styles)


def generate_ass_subtitles(talk_words: list, vo_words: list, ass_path: str, font_path: str, vo_offset: float = 5.0) -> str:
    """
    Generate an ASS subtitle file with TikTok-style captions.
    Single layer, clean boxes. Groups words into chunks of 3.
    """
    font_name = os.path.splitext(os.path.basename(font_path))[0].replace("-", " ")
    style = pick_subtitle_style()
    print(f"[CAP] Generating ASS subtitles -> {ass_path}")
    print(f"      Font: {font_name} | Style: {style['desc']}")

    s = style
    header = f"""[Script Info]
Title: Captions
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{s['fontsize']},{s['primary']},&H000000FF,{s['outline_col']},{s['back']},{s['bold']},0,0,0,100,100,0,0,{s['border_style']},{s['outline']},{s['shadow']},2,40,40,400,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def format_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        sec = int(seconds % 60)
        cs = int((seconds % 1) * 100)
        return f"{h}:{m:02d}:{sec:02d}.{cs:02d}"

    def words_to_events(words: list, time_offset: float = 0.0) -> list:
        events = []
        chunk_size = 3
        i = 0
        while i < len(words):
            chunk = words[i:i + chunk_size]
            text = " ".join(w["word"] for w in chunk)
            start = chunk[0]["start"] + time_offset
            end = chunk[-1]["end"] + time_offset
            end = max(end, start + 0.3)
            events.append(
                f"Dialogue: 0,{format_time(start)},{format_time(end)},Default,,0,0,0,,"
                f"{{\\an2}}{text}"
            )
            i += chunk_size
        return events

    events = []
    if talk_words:
        events.extend(words_to_events(talk_words, time_offset=0.0))
    if vo_words:
        events.extend(words_to_events(vo_words, time_offset=vo_offset))

    with open(ass_path, "w") as f:
        f.write(header)
        f.write("\n".join(events) + "\n")

    print(f"      Created {len(events)} caption events")
    return ass_path


## ── Top-performing photos (comment/uncomment to change) ──────────────────────
# To go back to random selection from all photos, comment out TOP_PHOTOS
# and the pick_image function will fall through to random selection.
# TOP_PHOTOS = [
#     "photo_02.jpeg",
#     "latina3.jpg",
# ]
TOP_PHOTOS = None
## ─────────────────────────────────────────────────────────────────────────────


def pick_image(photos_dir: str, choice: str = None) -> str:
    """Pick an image from the photos directory. Random if no choice given."""
    files = sorted(
        f for f in os.listdir(photos_dir)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    )
    if not files:
        raise FileNotFoundError(f"No images found in {photos_dir}/")

    if choice:
        if choice in files:
            return os.path.join(photos_dir, choice)
        matches = [f for f in files if choice.lower() in f.lower()]
        if matches:
            return os.path.join(photos_dir, matches[0])
        raise FileNotFoundError(f"No image matching '{choice}' in {photos_dir}/")

    # If TOP_PHOTOS is set, only pick from those
    if TOP_PHOTOS:
        available = [f for f in TOP_PHOTOS if f in files]
        if not available:
            print(f"WARNING: None of TOP_PHOTOS {TOP_PHOTOS} found in {photos_dir}/, falling back to random")
        else:
            picked = random.choice(available)
            return os.path.join(photos_dir, picked)

    picked = random.choice(files)
    return os.path.join(photos_dir, picked)


def upload_image(image_path: str) -> str:
    """Upload a local image via the Higgsfield SDK and return its URL."""
    print(f"[2/4] Uploading image: {image_path}")
    image_url = higgsfield_client.upload_file(image_path)
    print(f"      Uploaded: {image_url}")
    return image_url


def animate_talking(image_url: str, hook: str) -> str:
    """Video 1: Kling 3.0 — she speaks the Spanish hook to camera."""
    prompt = (
        f"The woman looks directly at the camera with a warm, confident expression and speaks clearly in Spanish, "
        f"saying exactly: \"{hook}\" "
        f"Her lips move clearly and expressively as she talks. "
        f"Friendly smile, natural head movement, warm eye contact, positive empowering energy. "
        f"Cinematic lighting, shallow depth of field, 5 seconds."
    )
    print(f"[3/5] Animating TALKING video (Kling 3.0)...")
    print(f"      Prompt: {prompt}")
    result = higgsfield_client.subscribe(
        TALK_MODEL,
        arguments={
            "image_url": image_url,
            "prompt": prompt,
        },
    )
    video_url = result["video"]["url"]
    print(f"      Video ready: {video_url}")
    return video_url


def animate_reaction(image_url: str) -> str:
    """Video 2: Try Kling 2.1 → 2.6 → 3.0 (cheapest first, escalate on NSFW)."""
    prompt = (
        "The woman smiles warmly and radiates positive energy, eyes bright and full of joy. "
        "Confident, friendly expression, looking at camera like greeting a friend. "
        "Natural laugh, warm golden lighting, shallow depth of field, 5 seconds."
    )
    models = [
        (REACT_MODEL, "2.1"),
        ("kling-video/v2.6/pro/image-to-video", "2.6"),
        (TALK_MODEL, "3.0"),
    ]
    print(f"[4/5] Animating REACTION video...")
    print(f"      Prompt: {prompt}")
    for model, label in models:
        print(f"      Trying Kling {label}...")
        result = higgsfield_client.subscribe(
            model,
            arguments={
                "image_url": image_url,
                "prompt": prompt,
            },
        )
        if "video" in result:
            video_url = result["video"]["url"]
            print(f"      Video ready (Kling {label}): {video_url}")
            return video_url
        print(f"      Kling {label} flagged NSFW, trying next...")

    raise RuntimeError(f"Kling reaction video failed on all models: {result}")


def download(url: str, filename: str, step: str = "") -> str:
    """Download a URL to the output directory."""
    path = os.path.join(OUTPUT_DIR, filename)
    print(f"[5/5] Downloading {step}-> {path}")
    resp = requests.get(url, timeout=300)
    resp.raise_for_status()
    with open(path, "wb") as f:
        f.write(resp.content)
    return path


def pick_screen_recording() -> str:
    """Pick one random screen recording clip."""
    files = sorted(
        f for f in os.listdir(SCREEN_REC_DIR)
        if f.lower().endswith((".mp4", ".mov"))
    )
    if not files:
        raise FileNotFoundError(f"No clips found in {SCREEN_REC_DIR}/")
    picked = random.choice(files)
    path = os.path.join(SCREEN_REC_DIR, picked)
    print(f"      Screen rec: {picked}")
    return path


def pick_song() -> str:
    """Pick a random song from the songs directory."""
    files = sorted(
        f for f in os.listdir(SONGS_DIR)
        if f.lower().endswith((".mp3", ".wav", ".m4a", ".aac"))
    )
    if not files:
        raise FileNotFoundError(f"No songs found in {SONGS_DIR}/")
    picked = random.choice(files)
    path = os.path.join(SONGS_DIR, picked)
    print(f"      Song: {picked}")
    return path


def stitch_videos(talk_path: str, react_path: str, vo_path: str, ass_path: str, final_path: str, title_img_path: str = None) -> str:
    """
    Stitch final video (always 10s total):
      1. Talk video (5s, with audio — woman speaks Spanish hook)
      2. Random screen recording (2.5s)
      3. React video with ssUI.png overlay (2.5s)
    Plus: background song (low volume, full duration)
    Plus: voiceover audio starting after talk ends
    Plus: optional title overlay PNG (during talk segment)
    Screen recordings are scaled to 1080x1920 to match.
    """
    sr = pick_screen_recording()
    song = pick_song()
    talk_duration = 5.0
    sr_dur = 2.5
    react_dur = 2.5
    vo_delay_ms = int(talk_duration * 1000)
    print("[STITCH] Stitching final 10s video with ffmpeg...")

    ass_escaped = ass_path.replace("\\", "\\\\").replace(":", "\\:")
    fonts_escaped = FONTS_DIR.replace("\\", "\\\\").replace(":", "\\:")

    # Build input list
    inputs = [
        "-i", talk_path,     # 0: talk
        "-i", sr,            # 1: screen recording
        "-i", react_path,    # 2: react
        "-i", UI_OVERLAY,    # 3: ssUI.png
        "-i", song,          # 4: background song
        "-i", vo_path,       # 5: voiceover audio
    ]

    # Title overlay is input 6 if present
    if title_img_path:
        inputs.extend(["-i", title_img_path])  # 6: title PNG

    filter_complex = (
        # --- Talk: trim first, then scale/fps/format ---
        f"[0:v]trim=duration={talk_duration},setpts=PTS-STARTPTS,"
        f"scale=1080:1920:force_original_aspect_ratio=decrease,"
        f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p[talk_v];"
        f"[0:a]aresample=44100,atrim=duration={talk_duration},asetpts=PTS-STARTPTS[talk_a];"
        # --- Screen rec: trim, scale/fps/format, silent audio ---
        f"[1:v]trim=duration={sr_dur},setpts=PTS-STARTPTS,"
        f"scale=1080:1920:force_original_aspect_ratio=decrease,"
        f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p[sr_v];"
        f"anullsrc=r=44100:cl=stereo,atrim=duration={sr_dur}[sr_a];"
        # --- React: trim, scale/fps/format, overlay ssUI.png, silent audio ---
        f"[2:v]trim=duration={react_dur},setpts=PTS-STARTPTS,"
        f"scale=1080:1920:force_original_aspect_ratio=decrease,"
        f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p[react_trim];"
        f"[react_trim][3:v]overlay=0:0[react_v];"
        f"anullsrc=r=44100:cl=stereo,atrim=duration={react_dur}[react_a];"
        # --- Concat all 3 video segments ---
        "[talk_v][talk_a][sr_v][sr_a][react_v][react_a]"
        "concat=n=3:v=1:a=1[cat_v][concat_a];"
    )

    # Burn in captions, then optionally overlay title
    if title_img_path:
        filter_complex += (
            f"[cat_v]ass={ass_escaped}:fontsdir={fonts_escaped}[captioned];"
            f"[captioned][6:v]overlay=0:0:enable='between(t,0,{talk_duration})'[outv];"
        )
    else:
        filter_complex += (
            f"[cat_v]ass={ass_escaped}:fontsdir={fonts_escaped}[outv];"
        )

    vo_max_dur = 5.0
    filter_complex += (
        # --- Background song: trim to 10s, low volume ---
        "[4:a]atrim=duration=10,asetpts=PTS-STARTPTS,volume=0.08[song];"
        # --- Voiceover: delay to start after talk, trim to remaining time ---
        f"[5:a]atrim=duration={vo_max_dur},asetpts=PTS-STARTPTS,volume=1.8[vo_trim];"
        f"[vo_trim]adelay={vo_delay_ms}|{vo_delay_ms}[vo];"
        # --- Mix all 3 audio layers ---
        "[concat_a][song][vo]amix=inputs=3:duration=longest:dropout_transition=2[outa]"
    )

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-t", "10",
        final_path,
    ]

    has_title = "YES" if title_img_path else "no"
    print(f"      Segments: talk({talk_duration}s) → screenRec({sr_dur}s) → react+UI({react_dur}s)")
    print(f"      Song: {song} | Voiceover: {vo_path} | Title: {has_title}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"      ffmpeg stderr: {result.stderr[-500:]}")
        raise RuntimeError(f"ffmpeg failed with exit code {result.returncode}")

    print(f"      Final video: {final_path}")
    return final_path


def upload_to_firebase(local_path: str) -> str:
    """Upload the final video to Firebase Storage and return the public URL."""
    if not firebase_admin._apps:
        print("[FIREBASE] Skipped — no Firebase app initialized.")
        return ""
    filename = os.path.basename(local_path)
    name, ext = os.path.splitext(filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    blob_path = f"videos/{name}_{timestamp}{ext}"
    print(f"[FIREBASE] Uploading {filename} -> gs://somesome-a6df1.firebasestorage.app/{blob_path}")
    bucket = storage.bucket()
    blob = bucket.blob(blob_path)
    blob.upload_from_filename(local_path, content_type="video/mp4")
    blob.make_public()
    print(f"      Public URL: {blob.public_url}")
    return blob.public_url


def log_to_gsheet(
    image_name: str,
    hook: str,
    vo_script: str,
    firebase_url: str,
    final_path: str,
) -> None:
    """Append a row to the Google Sheets log."""
    if _gc is None:
        print("[GSHEET] Skipped — no service account configured.")
        return
    print(f"[GSHEET] Logging to Google Sheets...")
    sh = _gc.open_by_key(GSHEET_ID)
    try:
        ws = sh.worksheet("Latam Female Ads")
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title="Latam Female Ads", rows=1000, cols=7)

    # Add headers if sheet is empty
    if not ws.get_all_values():
        ws.append_row(["Timestamp", "Image", "Hook", "Voiceover Script", "Firebase URL", "Local Path", "Version"])

    ws.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        image_name,
        hook,
        vo_script,
        firebase_url,
        final_path,
        "v3",
    ])
    row_count = len(ws.get_all_values()) - 1
    print(f"      Row added ({row_count} total entries)")
    print(f"      Sheet URL: {sh.url}")


def main():
    # Args: [image_name]
    image_choice = sys.argv[1] if len(sys.argv) > 1 else None

    # Step 1: GPT generates the Spanish ad hook
    hook = generate_hook()

    # Step 2: Pick a photo from femalePhotosV3
    image_path = pick_image(PHOTOS_DIR, image_choice)
    print(f"      Selected: {image_path}")

    # Step 3: Upload it (once — reuse URL for both videos)
    basename = os.path.splitext(os.path.basename(image_path))[0]
    image_url = upload_image(image_path)

    # Step 4a: Check if react video already exists in girlsChat cache
    # (saves tokens + time if this photo was already animated)
    react_cache_path = os.path.join("girlsChat", f"{basename}_react.mp4")
    if os.path.exists(react_cache_path):
        print(f"[CACHE HIT] React video found: {react_cache_path} — skipping generation")
        react_path = react_cache_path
    else:
        print(f"[CACHE MISS] No react video for {basename} — generating new one")
        react_url = animate_reaction(image_url)
        react_path = download(react_url, f"{basename}_react.mp4", "react ")
        # Save to girlsChat cache for future runs
        os.makedirs("girlsChat", exist_ok=True)
        import shutil
        shutil.copy2(react_path, react_cache_path)
        print(f"      Cached react video -> {react_cache_path}")

    # Step 4b: Generate talk video (always new — hook changes each run)
    talk_url = animate_talking(image_url, hook)
    talk_path = download(talk_url, f"{basename}_talk.mp4", "talk ")

    # Step 6: Generate Spanish voiceover (GPT script + ElevenLabs TTS)
    vo_script = generate_voiceover_script()
    vo_path = os.path.join(OUTPUT_DIR, f"{basename}_vo.mp3")
    generate_voiceover_audio(vo_script, vo_path)

    # Step 7: Generate captions via Whisper + random font
    talk_words = transcribe_audio(talk_path)
    vo_words = transcribe_audio(vo_path)
    font_path = pick_font()
    ass_path = os.path.join(OUTPUT_DIR, f"{basename}_captions.ass")
    generate_ass_subtitles(talk_words, vo_words, ass_path, font_path, vo_offset=5.0)

    # Step 7.5: 40% chance to add a Spanish TikTok-style title overlay
    title_img_path = None
    if random.random() < 0.4:
        title_text = generate_title()
        title_img_path = os.path.join(OUTPUT_DIR, f"{basename}_title.png")
        render_title_image(title_text, font_path, title_img_path)

    # Step 8: Stitch everything together (10s: talk 5s + screenRec 2.5s + react+UI 2.5s)
    final_path = os.path.join(OUTPUT_DIR, f"{basename}_final_v3.mp4")
    stitch_videos(talk_path, react_path, vo_path, ass_path, final_path, title_img_path)

    # Step 9: Upload final video to Firebase Storage
    firebase_url = upload_to_firebase(final_path)

    # Step 10: Log to Google Sheets
    log_to_gsheet(
        image_name=os.path.basename(image_path),
        hook=hook,
        vo_script=vo_script,
        firebase_url=firebase_url,
        final_path=final_path,
    )

    print(f"\n{'='*50}")
    print(f"  Hook:      \"{hook}\"")
    print(f"  Voiceover: \"{vo_script}\"")
    print(f"  Source:    {image_path}")
    print(f"  Talk vid:  {talk_path}")
    print(f"  React vid: {react_path}")
    print(f"  FINAL:     {final_path}")
    print(f"  Firebase:  {firebase_url}")
    print(f"  Log:       Google Sheets — {GSHEET_ID}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
