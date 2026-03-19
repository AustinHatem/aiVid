import higgsfield_client
import requests
import subprocess
import os
import sys
import random
from openai import OpenAI

# --- Config ---
# Video 1: Kling 3.0 — speaking the hook (native audio)
TALK_MODEL = "kling-video/v3.0/pro/image-to-video"
# Video 2: Kling 2.1 — silent reaction clip (laughing/smiling)
REACT_MODEL = "kling-video/v2.1/pro/image-to-video"
PHOTOS_DIR = "femalePhotos"
SCREEN_REC_DIR = "screenRecording"
SONGS_DIR = "songs"
OUTPUT_DIR = "output"
UI_OVERLAY = "ssUI.png"

# Female voices for OpenAI TTS (all sound natural/warm)
FEMALE_VOICES = ["nova", "shimmer", "alloy"]

# Example voiceover scripts (~9 seconds each) to teach GPT the style
EXAMPLE_VOICEOVERS = [
    "Some Some is a chat app where you can meet amazing ladies and chat with them immediately. There are a bunch of new people every day!",
    "Some Some video chat app is the safest most secure online platform available today. Download now to see what everyone is talking about.",
    "This app is going crazy viral. Video chat with strangers from all over the world instantly.",
    "Latina ladies are waiting to live video chat with you right now on Some Some App.",
]

# Example hooks to teach GPT the style and tone
EXAMPLE_HOOKS = [
    "Are you looking for secured video chat?",
    "Looking to meet new people?",
    "Want to talk to girls like me?",
    "The Some Some App is blowing up",
    "The best app for chatting with new people, Some Some",
    "Have you ever tried to video chat with real people?",
    "Enjoy your time with beautiful users all over the world",
    "Exclusive ladies are waiting to video chat on Some Some",
    "Some Some is the most secured video chat app",
    "Want to talk with mommy like me?",
]

os.makedirs(OUTPUT_DIR, exist_ok=True)

openai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def generate_hook() -> str:
    """Use GPT to generate a short, punchy 5-second ad hook for Some Some."""
    print("[1/4] Generating ad hook...")
    examples_block = "\n".join(f"- {h}" for h in EXAMPLE_HOOKS)
    resp = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You write viral short-form video ad hooks for the Some Some app — "
                    "a secured video chat app where you can meet and talk to real, beautiful people worldwide.\n\n"
                    "Rules:\n"
                    "- The hook is spoken directly to camera by an attractive woman.\n"
                    "- ONE sentence, under 15 words, takes ~5 seconds to say.\n"
                    "- Flirty, confident, curiosity-driven tone.\n"
                    "- Must mention 'Some Some' by name.\n"
                    "- Create curiosity, urgency, or a personal invitation.\n"
                    "- Do NOT repeat the examples — come up with something fresh.\n"
                    "- Do NOT use hashtags, emojis, or quotation marks.\n"
                    "- Return ONLY the raw sentence, nothing else.\n\n"
                    f"Here are example hooks for reference:\n{examples_block}"
                ),
            },
            {
                "role": "user",
                "content": "Write a new, unique 5-second spoken ad hook for Some Some.",
            },
        ],
        temperature=1.1,
        max_tokens=60,
    )
    hook = resp.choices[0].message.content.strip().strip('"').strip("'")
    print(f"      Hook: \"{hook}\"")
    return hook


def generate_voiceover_script() -> str:
    """Use GPT to generate a ~9-second voiceover script for Some Some."""
    print("[VO] Generating voiceover script...")
    examples_block = "\n".join(f"- {v}" for v in EXAMPLE_VOICEOVERS)
    resp = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You write voiceover scripts for short-form video ads for the Some Some app — "
                    "a secured video chat app where you can meet and talk to real, beautiful people worldwide.\n\n"
                    "Rules:\n"
                    "- The voiceover is read by a warm, friendly female narrator.\n"
                    "- It must be 2-3 sentences, around 20-30 words total.\n"
                    "- It should take EXACTLY about 9 seconds to say at a natural pace.\n"
                    "- Enthusiastic, inviting, conversational tone.\n"
                    "- Must mention 'Some Some' by name at least once.\n"
                    "- Highlight features like: video chat, meeting new people, security, global users, beautiful people.\n"
                    "- Do NOT repeat the examples — come up with something fresh and original.\n"
                    "- Do NOT use hashtags, emojis, or quotation marks.\n"
                    "- Return ONLY the raw voiceover text, nothing else.\n\n"
                    f"Here are example voiceovers for reference:\n{examples_block}"
                ),
            },
            {
                "role": "user",
                "content": "Write a new, unique ~9-second voiceover script for a Some Some ad.",
            },
        ],
        temperature=1.1,
        max_tokens=100,
    )
    script = resp.choices[0].message.content.strip().strip('"').strip("'")
    print(f"      Script: \"{script}\"")
    return script


def generate_voiceover_audio(script: str, output_path: str) -> str:
    """Use OpenAI TTS to generate a female voiceover audio file."""
    voice = random.choice(FEMALE_VOICES)
    print(f"[VO] Generating TTS audio (voice: {voice})...")
    response = openai.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=script,
        speed=0.95,  # slightly slower for clarity
    )
    with open(output_path, "wb") as f:
        f.write(response.content)
    print(f"      Voiceover saved: {output_path}")
    return output_path


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
        f"The woman looks directly at the camera and speaks naturally, saying: \"{hook}\" "
        f"Her lips move clearly and expressively as she talks. "
        f"Subtle head movement, natural facial expressions, confident energy. "
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
    """Video 2: Kling 2.1 — she laughs/smiles silently (b-roll reaction)."""
    prompt = (
        "The woman smiles warmly then laughs naturally, eyes bright and engaged. "
        "Gentle head tilt, relaxed and happy expression, looking at camera. "
        "Soft natural lighting, shallow depth of field, 5 seconds."
    )
    print(f"[4/5] Animating REACTION video (Kling 2.1)...")
    print(f"      Prompt: {prompt}")
    result = higgsfield_client.subscribe(
        REACT_MODEL,
        arguments={
            "image_url": image_url,
            "prompt": prompt,
        },
    )
    video_url = result["video"]["url"]
    print(f"      Video ready: {video_url}")
    return video_url


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


def stitch_videos(talk_path: str, react_path: str, vo_path: str, final_path: str) -> str:
    """
    Stitch final video:
      1. Talk video (5s, with audio)
      2. Random screen recording #1 (3.5s)
      3. React video with ssUI.png overlay (3s)
      4. Random screen recording #2 (3.5s)
    Plus: background song (low volume, full duration)
    Plus: voiceover audio starting at 5s (after talk ends)
    Screen recordings are scaled to 1080x1920 to match.
    """
    sr1, sr2 = pick_screen_recordings()
    song = pick_song()
    print("[STITCH] Stitching final video with ffmpeg...")

    # Total duration: 5 + 3.5 + 3 + 3.5 = 15s
    # Voiceover starts at 5s (after talk), plays over segments 2-4

    # Inputs:
    #   0 = talk, 1 = screen rec 1, 2 = react, 3 = screen rec 2,
    #   4 = ssUI.png, 5 = background song, 6 = voiceover
    cmd = [
        "ffmpeg", "-y",
        "-i", talk_path,     # 0: talk
        "-i", sr1,           # 1: screen recording 1
        "-i", react_path,    # 2: react
        "-i", sr2,           # 3: screen recording 2
        "-i", UI_OVERLAY,    # 4: ssUI.png
        "-i", song,          # 5: background song
        "-i", vo_path,       # 6: voiceover audio
        "-filter_complex",
        # --- Talk: use as-is (already 1080x1920) ---
        "[0:v]setpts=PTS-STARTPTS[talk_v];"
        "[0:a]asetpts=PTS-STARTPTS[talk_a];"

        # --- Screen rec 1: scale to 1080x1920, trim to 3.5s, add silent audio ---
        "[1:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,trim=duration=3.5,setpts=PTS-STARTPTS[sr1_v];"
        "anullsrc=r=44100:cl=stereo[s1];[s1]atrim=duration=3.5[sr1_a];"

        # --- React: trim to 3s, overlay ssUI.png, add silent audio ---
        "[2:v]trim=duration=3,setpts=PTS-STARTPTS[react_trim];"
        "[react_trim][4:v]overlay=0:0[react_v];"
        "anullsrc=r=44100:cl=stereo[s2];[s2]atrim=duration=3[react_a];"

        # --- Screen rec 2: scale to 1080x1920, trim to 3.5s, add silent audio ---
        "[3:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,trim=duration=3.5,setpts=PTS-STARTPTS[sr2_v];"
        "anullsrc=r=44100:cl=stereo[s3];[s3]atrim=duration=3.5[sr2_a];"

        # --- Concat all 4 video segments ---
        "[talk_v][talk_a][sr1_v][sr1_a][react_v][react_a][sr2_v][sr2_a]"
        "concat=n=4:v=1:a=1[outv][concat_a];"

        # --- Background song: trim to 15s, low volume ---
        "[5:a]atrim=duration=15,asetpts=PTS-STARTPTS,volume=0.08[song];"

        # --- Voiceover: delay by 5s (starts after talk), trim to 10s max ---
        "[6:a]atrim=duration=10,asetpts=PTS-STARTPTS,volume=1.8[vo_trim];"
        "[vo_trim]adelay=5000|5000[vo];"

        # --- Mix all 3 audio layers: concat audio + song + voiceover ---
        "[concat_a][song][vo]amix=inputs=3:duration=first:dropout_transition=2[outa]",

        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        final_path,
    ]

    print(f"      Segments: talk(5s) → screenRec(3.5s) → react+UI(3s) → screenRec(3.5s)")
    print(f"      Song: {song} | Voiceover: {vo_path}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"      ffmpeg stderr: {result.stderr[-500:]}")
        raise RuntimeError(f"ffmpeg failed with exit code {result.returncode}")

    print(f"      Final video: {final_path}")
    return final_path


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

    # Step 6: Generate voiceover (GPT script + OpenAI TTS)
    vo_script = generate_voiceover_script()
    vo_path = os.path.join(OUTPUT_DIR, f"{basename}_vo.mp3")
    generate_voiceover_audio(vo_script, vo_path)

    # Step 7: Stitch everything together
    final_path = os.path.join(OUTPUT_DIR, f"{basename}_final.mp4")
    stitch_videos(talk_path, react_path, vo_path, final_path)

    print(f"\n{'='*50}")
    print(f"  Hook:      \"{hook}\"")
    print(f"  Voiceover: \"{vo_script}\"")
    print(f"  Source:    {image_path}")
    print(f"  Talk vid:  {talk_path}")
    print(f"  React vid: {react_path}")
    print(f"  FINAL:     {final_path}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
