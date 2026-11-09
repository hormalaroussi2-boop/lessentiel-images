#!/usr/bin/env python3
"""Fabrique un Reel vertical (1080x1920) dynamique à partir des slides d'un post.

Usage : python3 tools/make_reel.py posts/<dossier> [secondes_par_slide]
Sortie : posts/<dossier>/reel.mp4 + affiche le crédit musique à mettre dans la légende.

Style « actu rapide » : chaque slide plein écran sur fond flouté, zoom lent et fluide
(image suréchantillonnée pour éviter les saccades), transitions glissées entre les slides,
barre de progression, musique libre de droits (assets/music/*.m4a) en fondu.
"""
import glob, os, random, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = sys.argv[1]
dur = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
slides = sorted(glob.glob(os.path.join(d, "slide-*.jpg")),
                key=lambda p: int(p.rsplit("-", 1)[1].split(".")[0]))
if not slides:
    sys.exit("Aucune slide : lance d'abord tools/render.js")

FPS, T = 30, 0.45            # images/s, durée d'une transition
frames = int(dur * FPS)
parts = []
for i, s in enumerate(slides):
    out = os.path.join(d, f".reel-part-{i}.mp4")
    zoom_in = i % 2 == 0      # alterne zoom avant / arrière pour du rythme
    z = f"1+0.06*on/{frames}" if zoom_in else f"1.06-0.06*on/{frames}"
    vf = (
        f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        f"boxblur=40:3,eq=brightness=-0.25[bg];"
        f"[0:v]scale=4000:-1,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={frames}:s=1040x1300:fps={FPS}[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2-40,"
        # barre de progression rouge en bas
        f"drawbox=x=0:y=1880:w=1080:h=12:color=white@0.25:t=fill,"
        f"drawbox=x=0:y=1880:w='1080*({i}+t/{dur})/{len(slides)}':h=12:color=0xb3261e:t=fill,"
        f"format=yuv420p[v]"
    )
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", str(FPS),
                    "-t", str(dur), "-i", s, "-filter_complex", vf, "-map", "[v]",
                    "-r", str(FPS), "-t", str(dur), "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "18", out], check=True)
    parts.append(out)

# Enchaînement avec transitions glissées
inputs, chain, last = [], "", "[0:v]"
for p in parts:
    inputs += ["-i", p]
for i in range(1, len(parts)):
    off = i * (dur - T)
    lab = f"[x{i}]"
    chain += f"{last}[{i}:v]xfade=transition=slideleft:duration={T}:offset={off:.3f}{lab};"
    last = lab
total = len(parts) * dur - (len(parts) - 1) * T

music = sorted(glob.glob(os.path.join(REPO, "assets", "music", "*.m4a")))
track = random.choice(music) if music else None
if track:
    inputs += ["-i", track]
    a = f"[{len(parts)}:a]atrim=0:{total:.3f},afade=t=in:d=0.8,afade=t=out:st={total - 1.5:.3f}:d=1.5,volume=0.8[a]"
else:
    inputs += ["-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
    a = f"[{len(parts)}:a]anull[a]"
vmap = last if len(parts) > 1 else "[0:v]"
fc = chain + (f"{vmap}format=yuv420p[v];" if len(parts) > 1 else "[0:v]format=yuv420p[v];") + a

out = os.path.join(d, "reel.mp4")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + inputs +
               ["-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-movflags", "+faststart", out], check=True)
for p in parts:
    os.remove(p)
print(out)
if track:
    name = os.path.basename(track)
    credit = next((l.split(" | ") for l in open(os.path.join(REPO, "assets", "music", "CREDITS.txt"), encoding="utf-8")
                   if l.startswith(name)), None)
    if credit:
        print(f"CRÉDIT MUSIQUE (à mettre en fin de légende) : 🎵 {credit[1]} – {credit[2]} ({credit[3]})")
