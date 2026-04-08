from dotenv import load_dotenv
load_dotenv()

import glob
import os
import random
import subprocess
import sys
import textwrap
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, storage
import gspread
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ── Config ────────────────────────────────────────────────────────────────────
GIRLS_DIR = "girlsChat"
GUYS_DIR = "guysChat"
UI_OVERLAY = "ssUI2.png"
OUTPUT_DIR = "output"
SEG_DURATION = 3.0
TOTAL_DURATION = 9.0
WIDTH, HEIGHT = 1080, 1920
PIP_WIDTH = 270  # ~25% of frame width
PIP_MARGIN = 80  # px from edge
PIP_RADIUS = 30  # rounded corner radius in px
TEXT_FONT = "fonts/TikTokSans-VariableFont_opsz,slnt,wdth,wght.ttf"
TEXT_SIZE = 72
TEXT_MAX_WIDTH = 20  # chars per line for wrapping
GSHEET_ID = "1h1pPMEshYzfCyqA-xc4NHVcGotQk_-S_LzfFhPaPlhQ"
DEFAULT_NUM_VIDEOS = 10

EXAMPLE_TEXTS = [
    "okay so you swipe, you match, and it just throws you straight into a video call. no texting. nothing. just them, right there.",
    "i cannot go back to typing 'haha yeah' for three weeks. this app just skips all of that.",
    "the call starts automatically when you match and i was NOT ready but also it was the best thing ever.",
    "you can tell in 30 seconds if you vibe with someone. texting could never do that.",
    "there's no text chat and honestly that is so smart because you literally cannot hide.",
    "i was nervous for like two seconds and then they smiled and i completely forgot.",
    "swipe, match, live video. that's it. no games, no back and forth, nothing.",
    "people on here actually show up. like fully present. it's so different.",
    "it doesn't let you overthink it and that is exactly what i needed.",
    "no filtered version of yourself. just you on camera being a normal person.",
    "we matched and somehow talked for two hours. i don't even know how.",
    "first impressions are actually back and i'm obsessed with it.",
    "it's a little scary the first time and then you're like wait why was i texting strangers this whole time.",
    "the video just starts. ready or not. and honestly? respect.",
    "i matched and before i could fix my hair we were already live and it was perfect.",
    "this is what actually connecting with someone feels like and i forgot it was possible.",
    "no opener needed. no 'hey'. you just show up and it works.",
    "it's giving real life but make it an app.",
    "the fact that you're face to face from the very first second changes everything.",
    "i genuinely thought i'd be awkward and instead it was just… easy.",
    "no more matching with someone and then absolutely nothing happening. we are so done with that.",
    "you swipe right, they swipe right, and suddenly you're already talking. like actually talking.",
    "there's something about seeing someone's face that just tells you everything immediately.",
    "it's terrifying for a second and then it's the most refreshing thing you've used in a while.",
    "no algorithm, no endless scrolling, no paragraphs going nowhere. just real people.",
    "i matched and my stomach dropped and then we laughed for an hour straight.",
    "the second you match the call starts and suddenly the whole thing feels real.",
    "stop spending weeks building a vibe with someone you've never actually seen move or laugh.",
    "it's so simple it almost feels too easy. swipe. match. face to face. done.",
    "i didn't think an app could feel this human but here we are.",
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


def pick_random_videos(directory: str, count: int) -> list[str]:
    videos = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.lower().endswith(".mp4")
    ]
    if len(videos) < count:
        sys.exit(f"Need {count} .mp4 files in {directory}/, found {len(videos)}")
    picks = random.sample(videos, count)
    for p in picks:
        print(f"    {p}")
    return picks


def render_text_overlay(text_content: str, index: int) -> str:
    """Render centered white text with dark outline, TikTok variable font (thin weight)."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    text_path = os.path.join(OUTPUT_DIR, f"_text_overlay_{index}.png")

    wrapped = textwrap.fill(text_content, width=TEXT_MAX_WIDTH)

    font = ImageFont.truetype(TEXT_FONT, TEXT_SIZE)
    # Axes: opsz, wdth, wght, slnt
    font.set_variation_by_axes([36, 100, 600, 0])  # SemiBold weight

    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))

    # Draw thick black outline by stamping text at offsets
    outline_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    od = ImageDraw.Draw(outline_layer)
    outline_range = 5
    for dx in range(-outline_range, outline_range + 1):
        for dy in range(-outline_range, outline_range + 1):
            if dx * dx + dy * dy <= outline_range * outline_range:
                od.multiline_text(
                    (WIDTH // 2 + dx, HEIGHT // 2 + dy), wrapped,
                    font=font, fill=(0, 0, 0, 255), anchor="mm", align="center",
                    spacing=16,
                )

    # Draw main white text
    draw = ImageDraw.Draw(img)
    draw.multiline_text(
        (WIDTH // 2, HEIGHT // 2), wrapped,
        font=font, fill=(255, 255, 255, 255), anchor="mm", align="center",
        spacing=16,
    )

    result = Image.alpha_composite(outline_layer, img)
    result.save(text_path)
    return text_path


def generate_mask_and_shadow():
    """Generate PiP rounded-corner mask and drop shadow PNGs."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    pip_height = int(PIP_WIDTH * (HEIGHT / WIDTH))
    scale = 4

    mask_path = os.path.join(OUTPUT_DIR, "_pip_mask.png")
    big_w, big_h = PIP_WIDTH * scale, pip_height * scale
    mask = Image.new("L", (big_w, big_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, big_w - 1, big_h - 1],
        radius=PIP_RADIUS * scale, fill=255,
    )
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
        radius=PIP_RADIUS * scale, fill=(0, 0, 0, 200),
    )
    shadow = shadow.resize((shadow_w, shadow_h), Image.LANCZOS)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=18))
    shadow.save(shadow_path)

    return mask_path, shadow_path


def build_segment(bg_path: str, pip_path: str, mask_path: str, shadow_path: str,
                  text_path: str, output_path: str, label: str) -> str:
    """Build a single 3s segment: bg fullscreen + ssUI + text + PiP with shadow."""
    pip_height = int(PIP_WIDTH * (HEIGHT / WIDTH))
    sp = 40

    filter_complex = (
        f"[0:v]trim=duration={SEG_DURATION},setpts=PTS-STARTPTS,"
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
        f"fps=30,format=yuv420p[bg];"
        f"[1:v]trim=duration={SEG_DURATION},setpts=PTS-STARTPTS,"
        f"scale={PIP_WIDTH}:{pip_height}:force_original_aspect_ratio=decrease,"
        f"pad={PIP_WIDTH}:{pip_height}:(ow-iw)/2:(oh-ih)/2,"
        f"fps=30,format=yuva420p[pip_raw];"
        f"[pip_raw][3:v]alphamerge[pip];"
        f"[bg][2:v]overlay=0:0[with_ui];"
        f"[with_ui][5:v]overlay=0:0:format=auto[with_text];"
        f"[with_text][4:v]overlay=W-w-{PIP_MARGIN - sp}:{PIP_MARGIN - sp}:format=auto[with_shadow];"
        f"[with_shadow][pip]overlay=W-w-{PIP_MARGIN}:{PIP_MARGIN}[out]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", bg_path,
        "-i", pip_path,
        "-i", UI_OVERLAY,
        "-i", mask_path,
        "-i", shadow_path,
        "-i", text_path,
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-an",
        "-t", str(SEG_DURATION),
        output_path,
    ]

    print(f"  [{label}] {os.path.basename(bg_path)} + PiP {os.path.basename(pip_path)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr)
        sys.exit(f"ffmpeg failed on segment {label}: exit code {result.returncode}")
    return output_path


def concat_segments(seg_paths: list[str], output_path: str) -> str:
    """Concatenate segment videos into final output."""
    concat_file = os.path.join(OUTPUT_DIR, "_concat_list.txt")
    with open(concat_file, "w") as f:
        for p in seg_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr)
        sys.exit(f"ffmpeg concat failed: exit code {result.returncode}")
    return output_path


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


def log_to_gsheet(ad_text: str, firebase_url: str, final_path: str) -> None:
    """Append a row to the Google Sheets log."""
    if _gc is None:
        print("[GSHEET] Skipped — no service account configured.")
        return
    print("[GSHEET] Logging to Google Sheets...")
    sh = _gc.open_by_key(GSHEET_ID)
    try:
        ws = sh.worksheet("V4 Ads")
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title="V4 Ads", rows=1000, cols=5)

    if not ws.get_all_values():
        ws.append_row(["Timestamp", "Ad Text", "Firebase URL", "Local Path", "Version"])

    ws.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ad_text,
        firebase_url,
        final_path,
        "v4",
    ])
    row_count = len(ws.get_all_values()) - 1
    print(f"      Row added ({row_count} total entries)")


def build_one_video(index: int, total_videos: int, ad_text: str, mask_path: str, shadow_path: str) -> str:
    """Build a single 9s video (3 segments) with the given ad text."""
    print(f"\n{'=' * 50}")
    print(f"  Video {index + 1}/{total_videos}")
    print(f"  Text: \"{ad_text[:60]}...\"")
    print(f"{'=' * 50}")

    print(f"\n  Picking videos...")
    print(f"    Girls:")
    girls = pick_random_videos(GIRLS_DIR, 3)
    print(f"    Guys:")
    guys = pick_random_videos(GUYS_DIR, 3)

    print(f"  Rendering text overlay...")
    text_path = render_text_overlay(ad_text, index)

    segments_def = [
        (girls[0], guys[0], "Seg1: girl bg + guy pip"),
        (guys[1], girls[1], "Seg2: guy bg + girl pip"),
        (girls[2], guys[2], "Seg3: girl bg + guy pip"),
    ]

    print(f"  Building 3 segments...")
    seg_paths = []
    for i, (bg, pip, label) in enumerate(segments_def):
        seg_out = os.path.join(OUTPUT_DIR, f"_seg{i + 1}_v4_{index}.mp4")
        build_segment(bg, pip, mask_path, shadow_path, text_path, seg_out, label)
        seg_paths.append(seg_out)

    final_name = f"v4_ad_{index + 1:02d}.mp4"
    final_path = os.path.join(OUTPUT_DIR, final_name)
    print(f"  Concatenating...")
    concat_segments(seg_paths, final_path)

    firebase_url = upload_to_firebase(final_path)
    log_to_gsheet(ad_text, firebase_url, final_path)

    print(f"  DONE: {final_path}")
    return final_path


def main():
    num_videos = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_NUM_VIDEOS
    print("=" * 50)
    print(f"  V4 Pipeline — Generating {num_videos} videos")
    print("=" * 50)

    # Pick unique texts from examples
    texts = random.sample(EXAMPLE_TEXTS, num_videos)

    print("\nGenerating shared assets (mask + shadow)...")
    mask_path, shadow_path = generate_mask_and_shadow()
    print("  Done")

    results = []
    for i, text in enumerate(texts):
        path = build_one_video(i, num_videos, text, mask_path, shadow_path)
        results.append(path)

    print(f"\n{'=' * 50}")
    print(f"  ALL DONE — {len(results)} videos generated")
    for r in results:
        print(f"    {r}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
