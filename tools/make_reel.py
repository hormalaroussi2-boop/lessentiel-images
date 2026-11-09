#!/usr/bin/env python3
"""Fabrique un Reel vertical (1080x1920) dynamique, avec voix off, à partir des slides d'un post.

Usage : python3 tools/make_reel.py posts/<dossier> [--voice tom|siwis|none] [--sec 3.5]
Sortie : posts/<dossier>/reel.mp4 + affiche le crédit musique à mettre dans la légende.

- Voix off (Piper, voix française gratuite, installée/téléchargée automatiquement) :
  le texte lu pour chaque slide vient de posts/<dossier>/voix.txt (une ligne par slide, dans
  l'ordre) ; sinon il est déduit de post.json (titre + texte de chaque story).
  La durée de chaque slide s'adapte à la longueur du texte lu.
- Style « actu rapide » : slide plein écran sur fond flouté, zoom fluide, transitions glissées,
  barre de progression, musique libre (assets/music/*.m4a) baissée sous la voix.
"""
import glob, json, os, random, re, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICES = os.path.expanduser("~/voices")
HF = "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR"

args = sys.argv[1:]
d = args[0]
voice = args[args.index("--voice") + 1] if "--voice" in args else "siwis"
base = float(args[args.index("--sec") + 1]) if "--sec" in args else 3.5
slides = sorted(glob.glob(os.path.join(d, "slide-*.jpg")),
                key=lambda p: int(p.rsplit("-", 1)[1].split(".")[0]))
if not slides:
    sys.exit("Aucune slide : lance d'abord tools/render.js")
FPS, T = 30, 0.45


def run(*cmd, **kw):
    return subprocess.run(list(cmd), check=True, **kw)


def duration(f):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", f], capture_output=True, text=True).stdout)


def texts():
    vf = os.path.join(d, "voix.txt")
    if os.path.exists(vf):
        lines = [l.strip() for l in open(vf, encoding="utf-8") if l.strip()]
        return (lines + [""] * len(slides))[:len(slides)]
    pj = os.path.join(d, "post.json")
    if not os.path.exists(pj):
        return [""] * len(slides)
    post = json.load(open(pj, encoding="utf-8"))
    clean = lambda s: re.sub(r"<[^>]+>", "", s or "")
    ed = {"MATIN": "du matin", "APRÈS-MIDI": "de l'après-midi", "SOIR": "du soir"}.get(post.get("edition"), "du jour")
    out = []
    for s in post["slides"]:
        if s["type"] == "cover":
            out.append(f"L'essentiel {ed}. Voici ce qu'il faut retenir.")
        elif s["type"] == "story":
            out.append(f"{clean(s['title'])}. {clean(s['body'])}")
        else:
            out.append(f"{clean(s.get('question', ''))} Dites-le en commentaire, et abonnez-vous pour ne rien rater.")
    return out


def ensure_voice():
    try:
        import piper  # noqa: F401
    except ImportError:
        run(sys.executable, "-m", "pip", "install", "-q", "piper-tts")
    os.makedirs(VOICES, exist_ok=True)
    model = os.path.join(VOICES, f"fr_FR-{voice}-medium.onnx")
    for f in (model, model + ".json"):
        if not os.path.exists(f):
            run("curl", "-sSL", "-o", f, f"{HF}/{voice}/medium/{os.path.basename(f)}")
    return model


# 1. Voix off
voice_files = [None] * len(slides)
if voice != "none":
    model = ensure_voice()
    for i, t in enumerate(texts()):
        if not t:
            continue
        raw = os.path.join(d, f".voice-{i}-raw.wav")
        w = os.path.join(d, f".voice-{i}.wav")
        # Réglages pour une voix plus naturelle : rythme posé, intonation variée, pauses.
        run(sys.executable, "-m", "piper", "-m", model, "-f", raw, "--length-scale", "1.0",
            "--noise-scale", "0.6", "--noise-w-scale", "0.85", "--sentence-silence", "0.28",
            input=t, text=True, capture_output=True)
        # Traitement « studio » : voix plus chaude et plus claire, compressée, très légère réverb.
        run("ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-af",
            "highpass=f=80,equalizer=f=200:t=q:w=1:g=1.5,equalizer=f=3500:t=q:w=1.2:g=2.5,"
            "equalizer=f=7500:t=q:w=1:g=-2,acompressor=threshold=-20dB:ratio=3:attack=5:release=80:makeup=3dB,"
            "aecho=0.8:0.6:25:0.12,loudnorm=I=-16:TP=-1.5:LRA=7", "-ar", "44100", w)
        os.remove(raw)
        voice_files[i] = w
durs = [max(base, duration(v) + 0.7) if v else base for v in voice_files]
starts = [sum(durs[:i]) - i * T for i in range(len(slides))]
total = starts[-1] + durs[-1]

# 2. Un clip par slide (zoom fluide + barre de progression)
parts = []
for i, s in enumerate(slides):
    dur, frames = durs[i], int(durs[i] * FPS)
    out = os.path.join(d, f".reel-part-{i}.mp4")
    z = f"1+0.06*on/{frames}" if i % 2 == 0 else f"1.06-0.06*on/{frames}"
    # Une seule image en entrée : zoompan en génère toutes les frames (peu de mémoire),
    # l'image est suréchantillonnée (2600 px) pour un zoom sans saccades.
    vf = (
        f"[0:v]split[a][b];"
        f"[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        f"boxblur=40:3,eq=brightness=-0.25,loop=loop={frames}:size=1:start=0,"
        f"setpts=N/{FPS}/TB[bg];"
        f"[b]scale=2600:-1,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={frames}:s=1040x1300:fps={FPS}[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2-40:shortest=1,"
        f"drawbox=x=0:y=1880:w=1080:h=12:color=white@0.25:t=fill,"
        f"drawbox=x=0:y=1880:w='1080*({starts[i]:.3f}+t)/{total:.3f}':h=12:color=0xb3261e:t=fill,"
        f"format=yuv420p[v]"
    )
    run("ffmpeg", "-y", "-loglevel", "error",
        "-i", s, "-filter_complex", vf, "-map", "[v]", "-r", str(FPS), "-t", f"{dur:.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", out)
    parts.append(out)

# 3. Montage : transitions + voix + musique
inputs, fc, last = [], "", "[0:v]"
for p in parts:
    inputs += ["-i", p]
for i in range(1, len(parts)):
    fc += f"{last}[{i}:v]xfade=transition=slideleft:duration={T}:offset={starts[i]:.3f}[x{i}];"
    last = f"[x{i}]"
fc += f"{last}format=yuv420p[v];"
n = len(parts)
audio_labels = []
for i, v in enumerate(voice_files):
    if v:
        inputs += ["-i", v]
        ms = int((starts[i] + 0.25) * 1000)
        fc += f"[{n}:a]aresample=44100,aformat=channel_layouts=stereo,adelay={ms}|{ms}[v{i}];"
        audio_labels.append(f"[v{i}]")
        n += 1
music = sorted(glob.glob(os.path.join(REPO, "assets", "music", "*.m4a")))
track = random.choice(music) if music else None
if track:
    inputs += ["-i", track]
    vol = 0.18 if audio_labels else 0.8      # musique discrète sous la voix
    fc += (f"[{n}:a]atrim=0:{total:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.8,"
           f"afade=t=out:st={total - 1.5:.3f}:d=1.5,volume={vol}[m];")
    audio_labels.append("[m]")
    n += 1
if not audio_labels:
    inputs += ["-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
    audio_labels.append(f"[{n}:a]")
fc += "".join(audio_labels) + f"amix=inputs={len(audio_labels)}:duration=longest:normalize=0,apad[a]"

out = os.path.join(d, "reel.mp4")
run("ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
    "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-movflags", "+faststart", out)
for p in parts + [v for v in voice_files if v]:
    os.remove(p)
print(out, f"({total:.1f} s)")
if track:
    name = os.path.basename(track)
    credit = next((l.strip().split(" | ") for l in open(os.path.join(REPO, "assets", "music", "CREDITS.txt"), encoding="utf-8")
                   if l.startswith(name)), None)
    if credit:
        print(f"CRÉDIT MUSIQUE (à mettre en fin de légende) : 🎵 {credit[1]} – {credit[2]} ({credit[3]})")
