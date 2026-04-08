from dotenv import load_dotenv
load_dotenv()

import os
import sys
import random
import subprocess
import textwrap
import glob
from datetime import datetime
from openai import OpenAI
from elevenlabs.client import ElevenLabs
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import firebase_admin
from firebase_admin import credentials, storage
import gspread

# ── Config ────────────────────────────────────────────────────────────────────
VIDEOS_DIR = "femaleSuprised"
SWIPE_DIR = "screenRecording/screenSwiping"
SCREEN_REC_DIR = "screenRecording"
PIP_DIR = "girlsChat"
SONGS_DIR = "songs"
FONTS_DIR = "fonts"
OUTPUT_DIR = "output_v5"
UI_OVERLAY = "ssUI.png"
WIDTH, HEIGHT = 1080, 1920
TEXT_FONT = "fonts/TikTokSans-VariableFont_opsz,slnt,wdth,wght.ttf"
TEXT_SIZE = 72
TEXT_MAX_WIDTH = 20
PIP_WIDTH = 270
PIP_MARGIN = 80
PIP_RADIUS = 30
GSHEET_ID = "1h1pPMEshYzfCyqA-xc4NHVcGotQk_-S_LzfFhPaPlhQ"

# Segment durations
SEG1_DUR = 3.0   # Part 1: girl + hook text
SEG2_DUR = 5.5   # Part 2: screen swiping (~8s @ 1.5x speed)
SEG3_DUR = 2.5   # Part 3: screen recording
SEG4_DUR = 2.0   # Part 4: girl part2 + ssUI + PiP
TOTAL_DUR = SEG1_DUR + SEG2_DUR + SEG3_DUR + SEG4_DUR

# ElevenLabs voices
ELEVEN_VOICES = [
    "21m00Tcm4TlvDq8ikWAM",  # Rachel
    "EXAVITQu4vr4xnSDxMaL",  # Bella
    "MF3mGyEYCl7XYWbV9V6O",  # Elli
]

# Firebase + Google Sheets setup
_sa_files = glob.glob("*-firebase-adminsdk-*.json")
if _sa_files:
    _cred = credentials.Certificate(_sa_files[0])
    firebase_admin.initialize_app(_cred, {"storageBucket": "somesome-a6df1.firebasestorage.app"})
    _gc = gspread.service_account(filename=_sa_files[0])
else:
    _gc = None
    print("WARNING: No Firebase service account JSON found — uploads/logging will be skipped.")

EXAMPLE_HOOKS = [
    "OMG this app is INSANE",
    "I just discovered this new app and it's blowing me away",
    "ok but why is no one talking about this app",
    "Someone Somewhere is literally so addicting",
    "I can't stop matching with people on here",
    "this app has me on it for HOURS",
    "wait why is everyone on Someone Somewhere so cute",
    "no bc Someone Somewhere is actually so fun",
    "I'm literally obsessed with this app rn",
    "the people on Someone Somewhere are unreal",
]

EXAMPLE_VOICEOVERS = [
    "Someone Somewhere is a chat app where you can meet amazing people and chat with them immediately.",
    "This app is going crazy viral. Video chat with strangers from all over the world instantly.",
    "Someone Somewhere video chat app is the safest most secure platform available today.",
    "Beautiful people are waiting to live video chat with you right now on Someone Somewhere.",
]

os.makedirs(OUTPUT_DIR, exist_ok=True)
openai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
elevenlabs = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])


# ── GPT: hook generation ─────────────────────────────────────────────────────
def generate_hook() -> str:
    print("[HOOK] Generating hook via GPT...")
    examples_block = "\n".join(f"- {h}" for h in EXAMPLE_HOOKS)
    resp = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You write viral short-form video ad hooks for the Someone Somewhere app — "
                    "a secured video chat app where you can meet and talk to real, beautiful people worldwide.\n\n"
                    "Rules:\n"
                    "- The hook is displayed as text on screen over a video of a young woman reacting.\n"
                    "- ONE sentence, under 12 words, punchy and attention-grabbing.\n"
                    "- Write in Gen Z female voice — casual, excited, unfiltered, like a girl posting on TikTok.\n"
                    "- Use words like: literally, obsessed, insane, unreal, no bc, ok but, lowkey, im sorry but, etc.\n"
                    "- Lowercase is fine. It should feel like a real text or caption, not an ad.\n"
                    "- Must mention 'Someone Somewhere' by name.\n"
                    "- Create curiosity, hype, or FOMO.\n"
                    "- Do NOT repeat the examples — come up with something fresh.\n"
                    "- Do NOT use hashtags, emojis, or quotation marks.\n"
                    "- Return ONLY the raw sentence, nothing else.\n\n"
                    f"Here are example hooks for reference:\n{examples_block}"
                ),
            },
            {"role": "user", "content": "Write a new, unique hook for Someone Somewhere."},
        ],
        temperature=1.1,
        max_tokens=40,
    )
    hook = resp.choices[0].message.content.strip().strip('"').strip("'")
    print(f"      Hook: \"{hook}\"")
    return hook


# ── GPT: voiceover script ────────────────────────────────────────────────────
def generate_voiceover_script() -> str:
    print("[VO] Generating voiceover script via GPT...")
    examples_block = "\n".join(f"- {v}" for v in EXAMPLE_VOICEOVERS)
    resp = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You write voiceover scripts for short-form video ads for the Someone Somewhere app — "
                    "a secured video chat app where you can meet and talk to real, beautiful people worldwide.\n\n"
                    "Rules:\n"
                    "- The voiceover is read by a warm, friendly female narrator.\n"
                    "- It must be 1-2 SHORT sentences, MAX 15 words total.\n"
                    "- It should take about 5-6 seconds to say at a natural pace. Keep it SHORT.\n"
                    "- Enthusiastic, inviting, conversational tone.\n"
                    "- Must mention 'Someone Somewhere' by name at least once.\n"
                    "- Highlight features like: video chat, meeting new people, security, global users.\n"
                    "- Do NOT repeat the examples — come up with something fresh.\n"
                    "- Do NOT use hashtags, emojis, or quotation marks.\n"
                    "- Return ONLY the raw voiceover text, nothing else.\n\n"
                    f"Here are example voiceovers for reference:\n{examples_block}"
                ),
            },
            {"role": "user", "content": "Write a new, unique ~6-second voiceover script for Someone Somewhere."},
        ],
        temperature=1.1,
        max_tokens=80,
    )
    script = resp.choices[0].message.content.strip().strip('"').strip("'")
    print(f"      Script: \"{script}\"")
    return script


# ── ElevenLabs TTS ────────────────────────────────────────────────────────────
def generate_voiceover_audio(script: str, output_path: str, max_duration: float = 7.0) -> str:
    voice_id = random.choice(ELEVEN_VOICES)
    print(f"[VO] Generating TTS audio (voice: {voice_id})...")
    audio = elevenlabs.text_to_speech.convert(
        voice_id=voice_id,
        text=script,
        model_id="eleven_multilingual_v2",
    )
    raw_path = output_path + ".raw.mp3"
    with open(raw_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)

    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", raw_path],
        capture_output=True, text=True
    )
    duration = float(probe.stdout.strip())
    print(f"      TTS duration: {duration:.1f}s (max: {max_duration}s)")

    if duration > max_duration:
        speed = duration / max_duration
        print(f"      Speeding up by {speed:.2f}x to fit...")
        subprocess.run(
            ["ffmpeg", "-y", "-i", raw_path, "-filter:a", f"atempo={speed}",
             "-c:a", "libmp3lame", "-q:a", "2", output_path],
            capture_output=True, text=True, timeout=30
        )
        os.remove(raw_path)
    else:
        os.rename(raw_path, output_path)

    print(f"      Voiceover saved: {output_path}")
    return output_path


# ── Whisper transcription ─────────────────────────────────────────────────────
def transcribe_audio(audio_path: str) -> list:
    print(f"[CAP] Transcribing {audio_path}...")
    with open(audio_path, "rb") as f:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json",
            timestamp_granularities=["word"],
        )
    words = [{"word": w.word, "start": w.start, "end": w.end} for w in transcript.words]
    print(f"      Got {len(words)} words")
    return words


# ── ASS subtitles ─────────────────────────────────────────────────────────────
def pick_font() -> str:
    files = sorted(
        f for f in os.listdir(FONTS_DIR)
        if f.lower().endswith((".ttf", ".otf"))
        and "VariableFont" not in f
    )
    if not files:
        raise FileNotFoundError(f"No fonts in {FONTS_DIR}/")
    picked = random.choice(files)
    print(f"      Caption font: {picked}")
    return os.path.join(FONTS_DIR, picked)


def pick_subtitle_style() -> dict:
    styles = [
        {"name": "white_outline", "desc": "White text, black outline",
         "primary": "&H00FFFFFF", "outline_col": "&H00000000", "back": "&H80000000",
         "border_style": 1, "outline": 5, "shadow": 2, "bold": -1, "fontsize": 88},
        {"name": "pink_box", "desc": "Dark text on pink/beige box",
         "primary": "&H00252525", "outline_col": "&H00C8D4E8", "back": "&H00C8D4E8",
         "border_style": 3, "outline": 22, "shadow": 0, "bold": -1, "fontsize": 80},
        {"name": "blue_box", "desc": "White text on blue/purple box",
         "primary": "&H00FFFFFF", "outline_col": "&H00B04828", "back": "&H00B04828",
         "border_style": 3, "outline": 22, "shadow": 0, "bold": -1, "fontsize": 80},
        {"name": "dark_box", "desc": "White text on dark box",
         "primary": "&H00FFFFFF", "outline_col": "&H4D282828", "back": "&H4D282828",
         "border_style": 3, "outline": 22, "shadow": 0, "bold": -1, "fontsize": 80},
    ]
    return random.choice(styles)


def generate_ass_subtitles(vo_words: list, ass_path: str, font_path: str, vo_offset: float) -> str:
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

    events = []
    chunk_size = 3
    i = 0
    while i < len(vo_words):
        chunk = vo_words[i:i + chunk_size]
        text = " ".join(w["word"] for w in chunk)
        start = chunk[0]["start"] + vo_offset
        end = chunk[-1]["end"] + vo_offset
        end = max(end, start + 0.3)
        events.append(
            f"Dialogue: 0,{format_time(start)},{format_time(end)},Default,,0,0,0,,"
            f"{{\\an2}}{text}"
        )
        i += chunk_size

    with open(ass_path, "w") as f:
        f.write(header)
        f.write("\n".join(events) + "\n")

    print(f"      Created {len(events)} caption events")
    return ass_path


# ── Text overlay rendering (v4 style) ────────────────────────────────────────
def render_text_overlay(text_content: str) -> str:
    text_path = os.path.join(OUTPUT_DIR, "_text_overlay.png")
    wrapped = textwrap.fill(text_content, width=TEXT_MAX_WIDTH)

    font = ImageFont.truetype(TEXT_FONT, TEXT_SIZE)
    font.set_variation_by_axes([36, 100, 600, 0])

    text_y = int(HEIGHT * 0.70)

    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    outline_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    od = ImageDraw.Draw(outline_layer)
    outline_range = 5
    for dx in range(-outline_range, outline_range + 1):
        for dy in range(-outline_range, outline_range + 1):
            if dx * dx + dy * dy <= outline_range * outline_range:
                od.multiline_text(
                    (WIDTH // 2 + dx, text_y + dy), wrapped,
                    font=font, fill=(0, 0, 0, 255), anchor="mm", align="center",
                    spacing=16,
                )

    draw = ImageDraw.Draw(img)
    draw.multiline_text(
        (WIDTH // 2, text_y), wrapped,
        font=font, fill=(255, 255, 255, 255), anchor="mm", align="center",
        spacing=16,
    )

    result = Image.alpha_composite(outline_layer, img)
    result.save(text_path)
    print(f"      Text overlay saved")
    return text_path


# ── PiP mask + shadow (v4 style) ─────────────────────────────────────────────
def generate_mask_and_shadow():
    pip_height = int(PIP_WIDTH * (HEIGHT / WIDTH))
    scale = 4

    mask_path = os.path.join(OUTPUT_DIR, "_pip_mask.png")
    big_w, big_h = PIP_WIDTH * scale, pip_height * scale
    mask = Image.new("L", (big_w, big_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, big_w - 1, big_h - 1], radius=PIP_RADIUS * scale, fill=255)
    mask = mask.resize((PIP_WIDTH, pip_height), Image.LANCZOS)
    mask.save(mask_path)

    shadow_pad = 40
    shadow_w = PIP_WIDTH + shadow_pad * 2
    shadow_h = pip_height + shadow_pad * 2
    shadow_path = os.path.join(OUTPUT_DIR, "_pip_shadow.png")
    shadow = Image.new("RGBA", (shadow_w * scale, shadow_h * scale), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [shadow_pad * scale, shadow_pad * scale,
         (shadow_pad + PIP_WIDTH) * scale - 1, (shadow_pad + pip_height) * scale - 1],
        radius=PIP_RADIUS * scale, fill=(0, 0, 0, 200))
    shadow = shadow.resize((shadow_w, shadow_h), Image.LANCZOS)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=18))
    shadow.save(shadow_path)

    return mask_path, shadow_path


# ── Pickers ───────────────────────────────────────────────────────────────────
def pick_part1_video() -> str:
    videos = sorted(f for f in os.listdir(VIDEOS_DIR) if f.endswith("_part1.mp4"))
    if not videos:
        sys.exit(f"No part1 videos in {VIDEOS_DIR}/")
    picked = random.choice(videos)
    print(f"      Part1: {picked}")
    return os.path.join(VIDEOS_DIR, picked)


def pick_part2_video(part1_name: str) -> str:
    part2_name = part1_name.replace("_part1.mp4", "_part2.mp4")
    path = os.path.join(VIDEOS_DIR, part2_name)
    if not os.path.exists(path):
        sys.exit(f"Missing part2: {path}")
    print(f"      Part2: {part2_name}")
    return path


def pick_swipe_video() -> str:
    videos = sorted(f for f in os.listdir(SWIPE_DIR) if f.lower().endswith(".mp4"))
    if not videos:
        sys.exit(f"No videos in {SWIPE_DIR}/")
    picked = random.choice(videos)
    print(f"      Swipe: {picked}")
    return os.path.join(SWIPE_DIR, picked)


def pick_screen_recording() -> str:
    videos = sorted(
        f for f in os.listdir(SCREEN_REC_DIR)
        if f.lower().endswith((".mp4", ".mov")) and os.path.isfile(os.path.join(SCREEN_REC_DIR, f))
    )
    if not videos:
        sys.exit(f"No videos in {SCREEN_REC_DIR}/")
    picked = random.choice(videos)
    print(f"      Screen rec: {picked}")
    return os.path.join(SCREEN_REC_DIR, picked)


def pick_pip_video() -> str:
    videos = sorted(f for f in os.listdir(PIP_DIR) if f.lower().endswith(".mp4"))
    if not videos:
        sys.exit(f"No videos in {PIP_DIR}/")
    picked = random.choice(videos)
    print(f"      PiP: {picked}")
    return os.path.join(PIP_DIR, picked)


def pick_song() -> str:
    files = sorted(
        f for f in os.listdir(SONGS_DIR)
        if f.lower().endswith((".mp3", ".wav", ".m4a", ".aac"))
    )
    if not files:
        raise FileNotFoundError(f"No songs in {SONGS_DIR}/")
    picked = random.choice(files)
    print(f"      Song: {picked}")
    return os.path.join(SONGS_DIR, picked)


# ── Final stitch (single ffmpeg pass like v1) ────────────────────────────────
def stitch_final(part1: str, swipe: str, screen_rec: str, part2: str,
                 pip_vid: str, text_overlay: str, mask: str, shadow: str,
                 vo_path: str, ass_path: str, song: str, final_path: str) -> str:
    """
    Single ffmpeg pass stitching 4 segments with voiceover, captions, and music.
    Seg1: part1 girl + hook text (3s)
    Seg2: screen swiping (3s)
    Seg3: screen recording (2.5s)
    Seg4: part2 girl + ssUI + PiP (2s)
    """
    pip_height = int(PIP_WIDTH * (HEIGHT / WIDTH))
    sp = 40
    vo_delay_ms = int(SEG1_DUR * 1000)  # voiceover starts after seg1

    ass_escaped = ass_path.replace("\\", "\\\\").replace(":", "\\:")
    fonts_escaped = FONTS_DIR.replace("\\", "\\\\").replace(":", "\\:")

    print("[STITCH] Building final video with ffmpeg...")

    inputs = [
        "-i", part1,          # 0: girl part1
        "-i", swipe,          # 1: screen swiping
        "-i", screen_rec,     # 2: screen recording
        "-i", part2,          # 3: girl part2
        "-i", pip_vid,        # 4: PiP video (girlsChat)
        "-i", UI_OVERLAY,     # 5: ssUI.png
        "-i", mask,           # 6: PiP mask
        "-i", shadow,         # 7: PiP shadow
        "-i", text_overlay,   # 8: hook text PNG
        "-i", song,           # 9: background song
        "-i", vo_path,        # 10: voiceover audio
    ]

    filter_complex = (
        # --- Seg1: girl part1 + hook text overlay ---
        f"[0:v]trim=duration={SEG1_DUR},setpts=PTS-STARTPTS,"
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p[s1_raw];"
        f"[s1_raw][8:v]overlay=0:0:format=auto,format=yuv420p[s1_v];"
        f"anullsrc=r=44100:cl=stereo,atrim=duration={SEG1_DUR}[s1_a];"

        # --- Seg2: screen swiping @ 1.5x (full video) ---
        f"[1:v]setpts=PTS/1.5,"
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p[s2_v];"
        f"anullsrc=r=44100:cl=stereo,atrim=duration={SEG2_DUR}[s2_a];"

        # --- Seg3: screen recording ---
        f"[2:v]trim=duration={SEG3_DUR},setpts=PTS-STARTPTS,"
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p[s3_v];"
        f"anullsrc=r=44100:cl=stereo,atrim=duration={SEG3_DUR}[s3_a];"

        # --- Seg4: girl part2 + ssUI + PiP with shadow ---
        f"[3:v]trim=duration={SEG4_DUR},setpts=PTS-STARTPTS,"
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p[s4_bg];"
        f"[4:v]trim=duration={SEG4_DUR},setpts=PTS-STARTPTS,"
        f"scale={PIP_WIDTH}:{pip_height}:force_original_aspect_ratio=decrease,"
        f"pad={PIP_WIDTH}:{pip_height}:(ow-iw)/2:(oh-ih)/2,"
        f"fps=30,format=yuva420p[pip_raw];"
        f"[pip_raw][6:v]alphamerge[pip];"
        f"[s4_bg][5:v]overlay=0:0[s4_ui];"
        f"[s4_ui][7:v]overlay=W-w-{PIP_MARGIN - sp}:{PIP_MARGIN - sp}:format=auto[s4_shadow];"
        f"[s4_shadow][pip]overlay=W-w-{PIP_MARGIN}:{PIP_MARGIN},format=yuv420p[s4_v];"
        f"anullsrc=r=44100:cl=stereo,atrim=duration={SEG4_DUR}[s4_a];"

        # --- Concat all 4 segments ---
        "[s1_v][s1_a][s2_v][s2_a][s3_v][s3_a][s4_v][s4_a]"
        "concat=n=4:v=1:a=1[cat_v][concat_a];"

        # --- Burn in captions ---
        f"[cat_v]ass={ass_escaped}:fontsdir={fonts_escaped}[outv];"

        # --- Background song: low volume ---
        f"[9:a]atrim=duration={TOTAL_DUR},asetpts=PTS-STARTPTS,volume=0.08[song];"

        # --- Voiceover: starts after seg1 ---
        f"[10:a]atrim=duration=7,asetpts=PTS-STARTPTS,volume=1.8[vo_trim];"
        f"[vo_trim]adelay={vo_delay_ms}|{vo_delay_ms}[vo];"

        # --- Mix all audio ---
        "[concat_a][song][vo]amix=inputs=3:duration=longest:dropout_transition=2[outa]"
    )

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        "-t", str(TOTAL_DUR),
        final_path,
    ]

    print(f"      Segments: part1+text({SEG1_DUR}s) → swipe({SEG2_DUR}s) → screenRec({SEG3_DUR}s) → part2+UI+PiP({SEG4_DUR}s)")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"      ffmpeg stderr: {result.stderr[-800:]}")
        sys.exit(f"ffmpeg stitch failed: exit code {result.returncode}")

    print(f"      Final video: {final_path}")
    return final_path


# ── Firebase upload + Google Sheets logging ───────────────────────────────────
def upload_to_firebase(local_path: str) -> str:
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


def log_to_gsheet(hook: str, vo_script: str, firebase_url: str, final_path: str) -> None:
    if _gc is None:
        print("[GSHEET] Skipped — no service account configured.")
        return
    print("[GSHEET] Logging to Google Sheets...")
    sh = _gc.open_by_key(GSHEET_ID)
    try:
        ws = sh.worksheet("V5 Ads")
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title="V5 Ads", rows=1000, cols=6)

    if not ws.get_all_values():
        ws.append_row(["Timestamp", "Hook", "Voiceover", "Firebase URL", "Local Path", "Version"])

    ws.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        hook,
        vo_script,
        firebase_url,
        final_path,
        "v5",
    ])
    row_count = len(ws.get_all_values()) - 1
    print(f"      Row added ({row_count} total entries)")


def main():
    print("=" * 60)
    print(f"  V5 — Full Pipeline ({TOTAL_DUR}s)")
    print(f"  Seg1: Girl + hook text ({SEG1_DUR}s)")
    print(f"  Seg2: Screen swiping ({SEG2_DUR}s)")
    print(f"  Seg3: Screen recording ({SEG3_DUR}s)")
    print(f"  Seg4: Girl + ssUI + PiP ({SEG4_DUR}s)")
    print(f"  + voiceover (after seg1) + captions + bg music")
    print("=" * 60)

    # Step 1: Generate hook + voiceover script via GPT
    hook = generate_hook()
    vo_script = generate_voiceover_script()

    # Step 2: Pick all videos
    print("\n[PICK] Selecting videos...")
    part1_path = pick_part1_video()
    part1_name = os.path.basename(part1_path)
    part2_path = pick_part2_video(part1_name)
    swipe_path = pick_swipe_video()
    screen_path = pick_screen_recording()
    pip_path = pick_pip_video()
    song_path = pick_song()

    basename = part1_name.replace("_part1.mp4", "")

    # Step 3: Render text overlay
    text_path = render_text_overlay(hook)

    # Step 4: Generate PiP mask + shadow
    mask_path, shadow_path = generate_mask_and_shadow()

    # Step 5: Generate voiceover audio (ElevenLabs TTS)
    vo_path = os.path.join(OUTPUT_DIR, f"{basename}_vo.mp3")
    generate_voiceover_audio(vo_script, vo_path)

    # Step 6: Transcribe voiceover for captions
    vo_words = transcribe_audio(vo_path)
    font_path = pick_font()
    ass_path = os.path.join(OUTPUT_DIR, f"{basename}_captions.ass")
    generate_ass_subtitles(vo_words, ass_path, font_path, vo_offset=SEG1_DUR)

    # Step 7: Stitch everything together
    final_path = os.path.join(OUTPUT_DIR, f"v5_{basename}_final.mp4")
    stitch_final(
        part1_path, swipe_path, screen_path, part2_path,
        pip_path, text_path, mask_path, shadow_path,
        vo_path, ass_path, song_path, final_path,
    )

    # Step 8: Upload to Firebase
    firebase_url = upload_to_firebase(final_path)

    # Step 9: Log to Google Sheets
    log_to_gsheet(hook, vo_script, firebase_url, final_path)

    print(f"\n{'=' * 60}")
    print(f"  Hook:      \"{hook}\"")
    print(f"  Voiceover: \"{vo_script}\"")
    print(f"  Firebase:  {firebase_url}")
    print(f"  FINAL:     {final_path} ({TOTAL_DUR}s)")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
