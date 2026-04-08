from dotenv import load_dotenv
load_dotenv()

import higgsfield_client
import requests
import os
import sys
import time

# ── Config ────────────────────────────────────────────────────────────────────
PHOTOS_DIR = "femalePhotos_v5"
OUTPUT_DIR = "femaleSuprised"

# Models — most advanced first, fallback on NSFW/failure
# Using same model format as working generate scripts
MODELS = [
    ("kling-video/v3.0/pro/image-to-video", "Kling 3.0"),
    ("kling-video/v2.6/pro/image-to-video", "Kling 2.6"),
    ("kling-video/v2.1/pro/image-to-video", "Kling 2.1"),
]

PROMPT = (
    "The woman smiles warmly and naturally, subtle movement, 5 seconds."
)


def get_photos(directory: str) -> list[str]:
    """Get all PNG photos sorted by name."""
    photos = sorted([
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ])
    print(f"Found {len(photos)} photos in {directory}/")
    for p in photos:
        print(f"    {os.path.basename(p)}")
    return photos


def upload_image(image_path: str) -> str:
    """Upload a local image via the Higgsfield SDK and return its URL."""
    print(f"  Uploading: {os.path.basename(image_path)}")
    image_url = higgsfield_client.upload_file(image_path)
    print(f"    URL: {image_url}")
    return image_url


def generate_video(image_url: str, photo_name: str) -> str:
    """Generate a surprised reaction video, trying models from most to least advanced."""
    print(f"  Generating surprised video for {photo_name}...")
    print(f"    Prompt: {PROMPT[:80]}...")

    for model, label in MODELS:
        print(f"    Trying {label} ({model})...")
        try:
            result = higgsfield_client.subscribe(
                model,
                arguments={
                    "image_url": image_url,
                    "prompt": PROMPT,
                },
            )
            if "video" in result:
                video_url = result["video"]["url"]
                print(f"    Success with {label}: {video_url}")
                return video_url
            else:
                print(f"    {label} returned no video (possibly NSFW), trying next...")
        except Exception as e:
            print(f"    {label} failed with error: {e}, trying next...")

    raise RuntimeError(f"All models failed for {photo_name}")


def download_video(url: str, filename: str) -> str:
    """Download a video URL to the output directory."""
    path = os.path.join(OUTPUT_DIR, filename)
    print(f"  Downloading -> {path}")
    resp = requests.get(url, timeout=300)
    resp.raise_for_status()
    with open(path, "wb") as f:
        f.write(resp.content)
    size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"    Saved ({size_mb:.1f} MB)")
    return path


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    photo_choice = sys.argv[1] if len(sys.argv) > 1 else None
    photos = get_photos(PHOTOS_DIR)
    if photo_choice:
        photos = [p for p in photos if os.path.splitext(os.path.basename(p))[0] == photo_choice or os.path.basename(p) == photo_choice]
    if len(photos) == 0:
        sys.exit(f"No photos found in {PHOTOS_DIR}/")

    print(f"\n{'=' * 60}")
    print(f"  Generating {len(photos)} surprised videos")
    print(f"  Output: {OUTPUT_DIR}/")
    print(f"{'=' * 60}\n")

    results = []
    for i, photo_path in enumerate(photos):
        photo_name = os.path.basename(photo_path)
        base_name = os.path.splitext(photo_name)[0]
        video_filename = f"{base_name}_surprised.mp4"

        print(f"\n[{i + 1}/{len(photos)}] {photo_name}")
        print(f"{'-' * 40}")

        # Upload
        image_url = upload_image(photo_path)

        # Generate
        video_url = generate_video(image_url, photo_name)

        # Download
        video_path = download_video(video_url, video_filename)
        results.append(video_path)

        print(f"  Done: {video_path}")

    print(f"\n{'=' * 60}")
    print(f"  ALL DONE — {len(results)} surprised videos generated")
    for r in results:
        print(f"    {r}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
