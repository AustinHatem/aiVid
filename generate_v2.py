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
# Video 2: Kling 2.1 — silent reaction clip (laughing/smiling)
REACT_MODEL = "kling-video/v2.1/pro/image-to-video"
PHOTOS_DIR = "femalePhotosV2"
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
# Best female voices on ElevenLabs (name -> voice_id)
ELEVEN_VOICES = [
    "21m00Tcm4TlvDq8ikWAM",  # Rachel — warm, calm
    "EXAVITQu4vr4xnSDxMaL",  # Bella — soft, friendly
    "MF3mGyEYCl7XYWbV9V6O",  # Elli — young, cheerful
]

# Example voiceover scripts (~9 seconds each) to teach GPT the style
EXAMPLE_VOICEOVERS = [
    "Someone Somewhere is where the baddies hang out. Real faces, real convos, no catfish energy.",
    "Stop scrolling and start talking. Someone Somewhere has the hottest people waiting to vibe with you right now.",
    "This app is blowing up for a reason. Someone Somewhere lets you video chat with gorgeous strangers instantly.",
    "Your DMs are dry but Someone Somewhere is not. Real video chat with real people who actually want to talk.",
]

# Example hooks to teach GPT the style and tone
EXAMPLE_HOOKS = [
    "You're not ready for Someone Somewhere",
    "Come find me on Someone Somewhere",
    "I dare you to match my energy",
    "Someone Somewhere has me addicted",
    "This app hits different honestly",
    "Why are you still single though",
    "I'm waiting for you on Someone Somewhere",
    "Someone Somewhere is lowkey dangerous",
    "POV you finally found Someone Somewhere",
    "Bet you can't keep up with me",
]

os.makedirs(OUTPUT_DIR, exist_ok=True)

openai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def generate_hook() -> str:
    """Use GPT to generate a short, punchy ad hook for Someone Somewhere."""
    print("[1/4] Generating ad hook (~5s)...")
    examples_block = "\n".join(f"- {h}" for h in EXAMPLE_HOOKS)
    resp = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You write viral short-form video ad hooks for the Someone Somewhere app — "
                    "a video chat app where you meet and talk to real, attractive people worldwide.\n\n"
                    "Rules:\n"
                    "- The hook is spoken directly to camera by a hot, confident young woman.\n"
                    "- ONE sentence, under 12 words, takes ~5 seconds to say.\n"
                    "- Edgy, flirty, provocative, slightly teasing — like a viral TikTok thirst trap.\n"
                    "- Think Gen Z energy: bold, unapologetic, attention-grabbing.\n"
                    "- Must mention 'Someone Somewhere' by name — always written as exactly 'Someone Somewhere' (two separate words).\n"
                    "- Place 'Someone Somewhere' where it flows naturally and can be clearly enunciated.\n"
                    "- Create intrigue, FOMO, or a direct personal challenge/invitation.\n"
                    "- Keep it PG-13 but make it spicy — suggestive, not explicit.\n"
                    "- Do NOT repeat the examples — come up with something fresh.\n"
                    "- Do NOT use hashtags, emojis, or quotation marks.\n"
                    "- Return ONLY the raw sentence, nothing else.\n\n"
                    f"Here are example hooks for reference:\n{examples_block}"
                ),
            },
            {
                "role": "user",
                "content": "Write a new, unique ~5-second spoken ad hook for Someone Somewhere.",
            },
        ],
        temperature=1.1,
        max_tokens=60,
    )
    hook = resp.choices[0].message.content.strip().strip('"').strip("'")
    print(f"      Hook: \"{hook}\"")
    return hook


def generate_voiceover_script() -> str:
    """Use GPT to generate a ~9-second voiceover script for Someone Somewhere."""
    print("[VO] Generating voiceover script...")
    examples_block = "\n".join(f"- {v}" for v in EXAMPLE_VOICEOVERS)
    resp = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You write voiceover scripts for short-form video ads for the Someone Somewhere app — "
                    "a video chat app where you meet and talk to real, attractive people worldwide.\n\n"
                    "Rules:\n"
                    "- The voiceover is read by a young, confident, slightly flirty female narrator.\n"
                    "- It must be 1-2 SHORT sentences, MAX 18 words total.\n"
                    "- It should take about 7-8 seconds to say at a natural pace. Keep it SHORT.\n"
                    "- Edgy, provocative, Gen Z energy — like narrating a viral TikTok.\n"
                    "- Suggestive and teasing but PG-13. Make it spicy, not explicit.\n"
                    "- Must mention 'Someone Somewhere' by name at least once.\n"
                    "- Create FOMO — make it sound like everyone's already on it and they're missing out.\n"
                    "- Highlight: hot people, instant video chat, the vibe, the thrill of meeting strangers.\n"
                    "- Do NOT repeat the examples — come up with something fresh and original.\n"
                    "- Do NOT use hashtags, emojis, or quotation marks.\n"
                    "- Return ONLY the raw voiceover text, nothing else.\n\n"
                    f"Here are example voiceovers for reference:\n{examples_block}"
                ),
            },
            {
                "role": "user",
                "content": "Write a new, unique ~9-second voiceover script for a Someone Somewhere ad.",
            },
        ],
        temperature=1.1,
        max_tokens=100,
    )
    script = resp.choices[0].message.content.strip().strip('"').strip("'")
    print(f"      Script: \"{script}\"")
    return script


def generate_voiceover_audio(script: str, output_path: str, max_duration: float = 9.0) -> str:
    """Use ElevenLabs TTS to generate a female voiceover audio file.
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

# Example titles to teach GPT the style
EXAMPLE_TITLES = [
    "you're not ready for this 🔥",
    "she's waiting for you 👀",
    "this app is lowkey addicting 😍",
    "POV: you found the vibe 🤭",
    "no more boring DMs 💅",
    "main character energy only 🫣",
]


def generate_title() -> str:
    """Use GPT to generate a short TikTok-style title with emoji."""
    print("[TITLE] Generating title...")
    examples_block = "\n".join(f"- {t}" for t in EXAMPLE_TITLES)
    resp = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You write short TikTok-style title overlays for viral video ads targeting Gen Z.\n\n"
                    "Rules:\n"
                    "- MAX 5-6 words total.\n"
                    "- Must include 1 emoji at the end.\n"
                    "- Edgy, flirty, provocative — like a thirst trap caption.\n"
                    "- Suggestive but PG-13. Spicy, not explicit.\n"
                    "- All lowercase or mixed case (not ALL CAPS).\n"
                    "- Do NOT repeat the examples — come up with something fresh.\n"
                    "- Do NOT use hashtags or quotation marks.\n"
                    "- Return ONLY the raw title, nothing else.\n\n"
                    f"Example titles:\n{examples_block}"
                ),
            },
            {
                "role": "user",
                "content": "Write a new, unique TikTok-style title overlay for a video chat app ad.",
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
    # Match emoji characters (including modifiers, ZWJ sequences, etc.)
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

    # Text font: TikTokSans-Bold
    tiktok_font_path = os.path.join(FONTS_DIR, "TikTokSans-Bold.ttf")
    font_size = 48
    try:
        text_font = ImageFont.truetype(tiktok_font_path, font_size)
    except Exception:
        text_font = ImageFont.truetype(font_path, font_size)

    # Emoji font: Apple Color Emoji (macOS system font)
    emoji_font = None
    emoji_font_path = "/System/Library/Fonts/Apple Color Emoji.ttc"
    if os.path.exists(emoji_font_path):
        try:
            emoji_font = ImageFont.truetype(emoji_font_path, font_size)
        except Exception:
            pass

    # Strip emojis for line-splitting (measure with text font only)
    parts = _split_emoji(title)
    text_only = "".join(s for is_emoji, s in parts if not is_emoji).strip()
    emoji_only = "".join(s for is_emoji, s in parts if is_emoji).strip()

    # Split text into lines (without emoji — emoji goes at end of last line)
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

    # Parse colors
    bg_color = tuple(int(bg_hex.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)) + (240,)
    text_color = text_hex

    pad_x, pad_y = 40, 24
    gap = 0
    corner_radius = 12
    y_start = 260

    for i, line in enumerate(lines):
        # On the last line, append emoji to measure total width
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

        # Draw rounded rectangle background
        draw.rounded_rectangle(
            [box_x, box_y, box_x + box_w, box_y + box_h],
            radius=corner_radius,
            fill=bg_color,
        )

        # Draw text
        text_x = box_x + pad_x - bbox[0]
        text_y = box_y + pad_y - bbox[1]
        draw.text((text_x, text_y), line, fill=text_color, font=text_font)

        # Draw emoji after text on last line
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
            "outline_col": "&H00C8D4E8",  # BGR for soft pinkish beige
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
            "outline_col": "&H00B04828",  # BGR for blue-purple
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
            "outline_col": "&H4D282828",  # dark gray at 70% opacity
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

    picked = random.choice(files)
    return os.path.join(photos_dir, picked)


def upload_image(image_path: str) -> str:
    """Upload a local image via the Higgsfield SDK and return its URL."""
    print(f"[2/4] Uploading image: {image_path}")
    image_url = higgsfield_client.upload_file(image_path)
    print(f"      Uploaded: {image_url}")
    return image_url


def animate_talking(image_url: str, hook: str) -> str:
    """Video 1: Kling 3.0 — she speaks the hook to camera."""
    prompt = (
        f"The woman looks directly at the camera with a confident expression and speaks clearly, saying exactly: \"{hook}\" "
        f"Her lips move clearly and expressively as she talks. "
        f"Subtle head movement, natural smile, bold eye contact, energetic vibe. "
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
        "The woman smiles brightly then laughs naturally, eyes bright and full of energy. "
        "Confident expression, relaxed and happy, looking at camera. "
        "Warm golden lighting, shallow depth of field, 5 seconds."
    )
    # Try models cheapest to most expensive, stop at first success
    models = [
        (REACT_MODEL, "2.1"),                                    # cheapest
        ("kling-video/v2.6/pro/image-to-video", "2.6"),         # mid
        (TALK_MODEL, "3.0"),                                     # most expensive
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


def pick_screen_recordings() -> tuple:
    """Pick two random (different) screen recording clips."""
    files = sorted(
        f for f in os.listdir(SCREEN_REC_DIR)
        if f.lower().endswith((".mp4", ".mov"))
    )
    if len(files) < 2:
        raise FileNotFoundError(f"Need at least 2 clips in {SCREEN_REC_DIR}/")
    picked = random.sample(files, 2)
    paths = [os.path.join(SCREEN_REC_DIR, f) for f in picked]
    print(f"      Screen recs: {picked[0]}, {picked[1]}")
    return paths[0], paths[1]


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
    Stitch final video (always 15s total):
      1. Talk video (5s, with audio)
      2. Random screen recording #1 (3.5s)
      3. React video with ssUI.png overlay (3s)
      4. Random screen recording #2 (3.5s)
    Plus: background song (low volume, full duration)
    Plus: voiceover audio starting after talk ends
    Plus: optional title overlay PNG (during talk segment)
    Screen recordings are scaled to 1080x1920 to match.
    """
    sr1, sr2 = pick_screen_recordings()
    song = pick_song()
    talk_duration = 5.0
    sr1_dur = 3.5
    react_dur = 3.0
    sr2_dur = 3.5
    vo_delay_ms = int(talk_duration * 1000)
    print("[STITCH] Stitching final video with ffmpeg...")

    ass_escaped = ass_path.replace("\\", "\\\\").replace(":", "\\:")
    fonts_escaped = FONTS_DIR.replace("\\", "\\\\").replace(":", "\\:")

    # Build input list and filter
    inputs = [
        "-i", talk_path,     # 0: talk
        "-i", sr1,           # 1: screen recording 1
        "-i", react_path,    # 2: react
        "-i", sr2,           # 3: screen recording 2
        "-i", UI_OVERLAY,    # 4: ssUI.png
        "-i", song,          # 5: background song
        "-i", vo_path,       # 6: voiceover audio
    ]

    # Title overlay is input 7 if present
    if title_img_path:
        inputs.extend(["-i", title_img_path])  # 7: title PNG

    filter_complex = (
        # --- Talk: trim first, then scale/fps/format for clean concat ---
        f"[0:v]trim=duration={talk_duration},setpts=PTS-STARTPTS,"
        f"scale=1080:1920:force_original_aspect_ratio=decrease,"
        f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p[talk_v];"
        f"[0:a]aresample=44100,atrim=duration={talk_duration},asetpts=PTS-STARTPTS[talk_a];"
        # --- Screen rec 1: trim first, then scale/fps/format, add silent audio ---
        f"[1:v]trim=duration={sr1_dur},setpts=PTS-STARTPTS,"
        f"scale=1080:1920:force_original_aspect_ratio=decrease,"
        f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p[sr1_v];"
        f"anullsrc=r=44100:cl=stereo,atrim=duration={sr1_dur}[sr1_a];"
        # --- React: trim first, then scale/fps/format, overlay ssUI.png, add silent audio ---
        f"[2:v]trim=duration={react_dur},setpts=PTS-STARTPTS,"
        f"scale=1080:1920:force_original_aspect_ratio=decrease,"
        f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p[react_trim];"
        f"[react_trim][4:v]overlay=0:0[react_v];"
        f"anullsrc=r=44100:cl=stereo,atrim=duration={react_dur}[react_a];"
        # --- Screen rec 2: trim first, then scale/fps/format, add silent audio ---
        f"[3:v]trim=duration={sr2_dur},setpts=PTS-STARTPTS,"
        f"scale=1080:1920:force_original_aspect_ratio=decrease,"
        f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p[sr2_v];"
        f"anullsrc=r=44100:cl=stereo,atrim=duration={sr2_dur}[sr2_a];"
        # --- Concat all 4 video segments ---
        "[talk_v][talk_a][sr1_v][sr1_a][react_v][react_a][sr2_v][sr2_a]"
        "concat=n=4:v=1:a=1[cat_v][concat_a];"
    )

    # Burn in captions, then optionally overlay title
    if title_img_path:
        filter_complex += (
            f"[cat_v]ass={ass_escaped}:fontsdir={fonts_escaped}[captioned];"
            f"[captioned][7:v]overlay=0:0:enable='between(t,0,{talk_duration})'[outv];"
        )
    else:
        filter_complex += (
            f"[cat_v]ass={ass_escaped}:fontsdir={fonts_escaped}[outv];"
        )

    vo_max_dur = 10.0
    filter_complex += (
        # --- Background song: trim to 15s, low volume ---
        "[5:a]atrim=duration=15,asetpts=PTS-STARTPTS,volume=0.08[song];"
        # --- Voiceover: delay to start after talk, trim to remaining time ---
        f"[6:a]atrim=duration={vo_max_dur},asetpts=PTS-STARTPTS,volume=1.8[vo_trim];"
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
        "-t", "15",
        final_path,
    ]

    has_title = "YES" if title_img_path else "no"
    print(f"      Segments: talk({talk_duration}s) → screenRec({sr1_dur}s) → react+UI({react_dur}s) → screenRec({sr2_dur}s)")
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
    ws = sh.sheet1

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
        "v2",
    ])
    row_count = len(ws.get_all_values()) - 1
    print(f"      Row added ({row_count} total entries)")
    print(f"      Sheet URL: {sh.url}")


def main():
    # Args: [image_name]
    image_choice = sys.argv[1] if len(sys.argv) > 1 else None

    # Step 1: GPT generates the ad hook
    hook = generate_hook()

    # Step 2: Pick a photo
    image_path = pick_image(PHOTOS_DIR, image_choice)
    print(f"      Selected: {image_path}")

    # Step 3: Upload it (once — reuse URL for both videos)
    image_url = upload_image(image_path)

    # Step 4: Generate both videos
    talk_url = animate_talking(image_url, hook)
    react_url = animate_reaction(image_url)

    # Step 5: Download both
    basename = os.path.splitext(os.path.basename(image_path))[0]
    talk_path = download(talk_url, f"{basename}_talk.mp4", "talk ")
    react_path = download(react_url, f"{basename}_react.mp4", "react ")

    # Step 6: Generate voiceover (GPT script + ElevenLabs TTS)
    vo_script = generate_voiceover_script()
    vo_path = os.path.join(OUTPUT_DIR, f"{basename}_vo.mp3")
    generate_voiceover_audio(vo_script, vo_path)

    # Step 7: Generate captions via Whisper + random font
    talk_words = transcribe_audio(talk_path)
    vo_words = transcribe_audio(vo_path)
    font_path = pick_font()
    ass_path = os.path.join(OUTPUT_DIR, f"{basename}_captions.ass")
    generate_ass_subtitles(talk_words, vo_words, ass_path, font_path, vo_offset=5.0)

    # Step 7.5: 40% chance to add a TikTok-style title overlay
    title_img_path = None
    if random.random() < 0.4:
        title_text = generate_title()
        title_img_path = os.path.join(OUTPUT_DIR, f"{basename}_title.png")
        render_title_image(title_text, font_path, title_img_path)

    # Step 8: Stitch everything together (with burned-in captions + optional title)
    final_path = os.path.join(OUTPUT_DIR, f"{basename}_final.mp4")
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
