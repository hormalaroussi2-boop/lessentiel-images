#!/usr/bin/env python3
"""Fabrique un Reel vertical (1080x1920, ~4 s par slide) à partir des slides d'un post.

Usage : python3 tools/make_reel.py posts/<dossier> [secondes_par_slide]
Sortie : posts/<dossier>/reel.mp4 (H.264 + piste audio silencieuse, format accepté par Instagram).
Chaque slide est posée au centre sur un fond flouté d'elle-même, avec un léger zoom.
"""
import glob, os, subprocess, sys

d = sys.argv[1]
dur = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
slides = sorted(glob.glob(os.path.join(d, "slide-*.jpg")),
                key=lambda p: int(p.rsplit("-", 1)[1].split(".")[0]))
if not slides:
    sys.exit("Aucune slide : lance d'abord tools/render.js")

fps = 30
frames = int(dur * fps)
parts = []
for i, s in enumerate(slides):
    out = os.path.join(d, f".reel-part-{i}.mp4")
    vf = (
        f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:2,eq=brightness=-0.15[bg];"
        f"[0:v]scale=1000:-2,zoompan=z='min(1+0.0008*on,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={frames}:s=1000x1250:fps={fps}[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]"
    )
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-t", str(dur), "-i", s,
                    "-filter_complex", vf, "-map", "[v]", "-r", str(fps), "-t", str(dur),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", out], check=True)
    parts.append(out)

lst = os.path.join(d, ".reel-list.txt")
with open(lst, "w") as f:
    f.writelines(f"file '{os.path.abspath(p)}'\n" for p in parts)
out = os.path.join(d, "reel.mp4")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-shortest", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out], check=True)
for p in parts + [lst]:
    os.remove(p)
print(out)
