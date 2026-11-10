"""Convert a clip (e.g. assets/loki_larp.mp4) into what pygame / the web build can play: numbered JPG frames + an OGG audio file.

    python tools/convert_video.py assets/loki_larp.mp4            # -> assets/loki_larp/frame_0001.jpg ..., audio.ogg, info.json
    python tools/convert_video.py clip.mp4 --fps 12 --width 400   # smaller = less memory

Needs ffmpeg on the PATH (Ubuntu / WSL: sudo apt install ffmpeg). Run it once on your machine, commit the result.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--fps", type=int, default=15, help="frames per second to keep (default 15)")
    ap.add_argument("--width", type=int, default=480, help="frame width in px, height keeps the aspect ratio (default 480)")
    ap.add_argument("--quality", type=int, default=5, help="JPG quality for ffmpeg, 2 = best, 31 = worst (default 5)")
    ap.add_argument("--out", default=None, help="output folder (default: next to the video, same name without .mp4)")
    a = ap.parse_args()
    if shutil.which("ffmpeg") is None:
        print("ffmpeg not found. Install it first (Ubuntu / WSL: sudo apt install ffmpeg).", file=sys.stderr)
        return 1
    src = Path(a.video)
    if not src.is_file():
        print(f"video not found: {src}", file=sys.stderr)
        return 1
    out = Path(a.out) if a.out else src.with_suffix("")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(src), "-vf", f"fps={a.fps},scale={a.width}:-2",
                    "-q:v", str(a.quality), str(out / "frame_%04d.jpg")], check=True)
    has_audio = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(src), "-vn", "-c:a", "libvorbis", "-q:a", "3",
                                str(out / "audio.ogg")]).returncode == 0 and (out / "audio.ogg").exists()
    frames = len(list(out.glob("frame_*.jpg")))
    size = sum(f.stat().st_size for f in out.iterdir())
    (out / "info.json").write_text(json.dumps({"fps": a.fps, "frames": frames, "seconds": round(frames / a.fps, 2),
                                               "audio": "audio.ogg" if has_audio else None}))
    print(f"{frames} frames at {a.fps} fps ({frames / a.fps:.1f} s), audio: {has_audio}, {size / 1e6:.1f} MB on disk")
    print(f"in memory as pygame surfaces: about {frames * a.width * (a.width * 9 // 16) * 4 / 1e6:.0f} MB if all are loaded (16:9 guess); the player should stream them")
    return 0


if __name__ == "__main__":
    sys.exit(main())
