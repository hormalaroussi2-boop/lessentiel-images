#!/usr/bin/env python3
"""Fabrique une vidéo ANIMÉE verticale (1080x1920) « Le saviez-vous ? » avec voix off.

Usage : python3 tools/make_anim.py posts/<dossier>
Entrée : posts/<dossier>/anim.json
  { "scenes": [
      { "type": "hook",    "voice": "...", "kicker": "LE SAVIEZ-VOUS ?", "title": "Texte <b>mot fort</b>", "image": "img-1.jpg", "credit": "Photo : ..." },
      { "type": "number",  "voice": "...", "number": 1619, "label": "Texte sous le nombre" },
      { "type": "stamp",   "voice": "...", "title": "Texte", "stamp": "VOLÉ" },
      { "type": "rain",    "voice": "...", "emoji": "👕", "title": "Texte" },
      { "type": "text",    "voice": "...", "title": "Texte" },
      { "type": "end",     "voice": "...", "title": "Question ?" }
  ] }
  - "voice" : texte lu (écrire les nombres en lettres, les noms comme ils se prononcent).
  - "image" (facultatif, toutes scènes) : photo libre en fond animé, "credit" obligatoire alors.
Sortie : posts/<dossier>/anim.mp4
Chaque scène dure le temps de sa voix (+ 0,4 s). Rendu image par image (déterministe) avec Playwright.
"""
import base64, json, os, subprocess, sys, tempfile, wave

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.expanduser("~/voices/fr_FR-tom-medium.onnx")
FPS, W, H = 30, 1080, 1920

d = sys.argv[1]
spec = json.load(open(os.path.join(d, "anim.json"), encoding="utf-8"))
scenes = spec["scenes"]
tmp = tempfile.mkdtemp()

# 1) Voix off, scène par scène
wavs, durs = [], []
for i, s in enumerate(scenes):
    w = os.path.join(tmp, f"v{i}.wav")
    subprocess.run([sys.executable, "-m", "piper", "-m", MODEL, "-f", w, "--length-scale", "0.93",
                    "--sentence-silence", "0.15"], input=s["voice"], text=True, check=True,
                   capture_output=True)
    with wave.open(w) as f:
        durs.append(f.getnframes() / f.getframerate() + 0.4)
    wavs.append(w)
total = sum(durs)

# Voix complète (avec 0,4 s de silence après chaque scène)
lst = os.path.join(tmp, "list.txt")
sil = os.path.join(tmp, "sil.wav")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=22050:cl=mono",
                "-t", "0.4", sil], check=True)
with open(lst, "w") as f:
    for w in wavs:
        f.write(f"file '{w}'\nfile '{sil}'\n")
voice = os.path.join(tmp, "voice.wav")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                "-ar", "44100", voice], check=True)

# 2) Page HTML animée : render(t) dessine l'état exact à l'instant t
for s in scenes:
    if s.get("image"):
        s["src"] = "data:image/jpeg;base64," + base64.b64encode(
            open(os.path.join(d, s["image"]), "rb").read()).decode()
html = r"""<!doctype html><html><head><meta charset="utf-8"><style>
*{margin:0;box-sizing:border-box}
body{width:1080px;height:1920px;overflow:hidden;background:#141414;font-family:'Inter',sans-serif;color:#f4efe4}
#bg{position:absolute;inset:0;background-size:cover;background-position:center;opacity:0}
#shade{position:absolute;inset:0;background:linear-gradient(180deg,rgba(20,20,20,.15) 0%,rgba(20,20,20,.55) 45%,rgba(20,20,20,.97) 72%)}
.blob{position:absolute;border-radius:50%;filter:blur(2px)}
#b1{width:900px;height:900px;background:#b3261e;opacity:.22;left:-300px;top:-200px}
#b2{width:700px;height:700px;background:#f4efe4;opacity:.06;right:-260px;bottom:200px}
#brand{position:absolute;top:90px;left:80px;right:80px;display:flex;justify-content:space-between;align-items:center;
 font-weight:900;font-size:40px;letter-spacing:3px;border-bottom:4px solid #f4efe4;padding-bottom:22px}
#brand span{background:#b3261e;padding:6px 16px;font-size:30px}
#stage{position:absolute;left:80px;right:80px;top:300px;bottom:260px;display:flex;flex-direction:column;justify-content:flex-end}
.kick{display:inline-block;align-self:flex-start;background:#b3261e;color:#fff;font-weight:900;font-size:58px;letter-spacing:4px;padding:16px 30px;margin-bottom:40px}
.title{font-family:'DejaVu Serif',serif;font-weight:700;font-size:96px;line-height:1.1}
.title b{color:#ff5a4f}
.word{display:inline-block;margin-right:.25em}
.num{font-weight:900;font-size:330px;line-height:1;color:#ff5a4f;letter-spacing:-8px}
.label{font-family:'DejaVu Serif',serif;font-size:72px;line-height:1.15;margin-top:30px}
.stamp{position:absolute;right:40px;top:120px;border:14px solid #ff5a4f;color:#ff5a4f;font-weight:900;font-size:170px;
 padding:10px 50px;letter-spacing:10px;border-radius:24px}
.drop{position:absolute;font-size:120px}
#credit{position:absolute;right:80px;top:180px;font-size:24px;color:rgba(244,239,228,.85);background:rgba(0,0,0,.45);padding:6px 12px}
#bar{position:absolute;left:0;bottom:0;height:16px;background:#b3261e}
#handle{position:absolute;bottom:90px;left:80px;font-weight:800;font-size:38px;letter-spacing:4px;opacity:.9}
</style></head><body>
<div id="bg"></div><div id="shade"></div><div class="blob" id="b1"></div><div class="blob" id="b2"></div>
<div id="brand">L'ESSENTIEL <span>LE SAVIEZ-VOUS ?</span></div>
<div id="credit"></div><div id="stage"></div><div id="handle">@LESSENTIEL.BEFR</div><div id="bar"></div>
<script>
const S=__SCENES__, D=__DURS__, TOTAL=__TOTAL__;
const ease=x=>1-Math.pow(1-Math.min(Math.max(x,0),1),3);
const back=x=>{x=Math.min(Math.max(x,0),1);const c=1.7;return 1+(c+1)*Math.pow(x-1,3)+c*Math.pow(x-1,2)};
const stage=document.getElementById('stage'),bg=document.getElementById('bg'),cr=document.getElementById('credit');
let cur=-1;
function words(html){ // découpe en mots en gardant les <b>
  const out=[];let bold=false;
  html.replace(/<b>/g,' \u0001 ').replace(/<\/b>/g,' \u0002 ').split(/\s+/).forEach(w=>{
    if(!w)return; if(w=='\u0001'){bold=true;return} if(w=='\u0002'){bold=false;return}
    out.push(`<span class="word">${bold?'<b>'+w+'</b>':w}</span>`)});
  return out.join(' ');
}
function build(i){
  const s=S[i];let h='';
  if(s.type=='hook') h=`<div class="kick">${s.kicker||'LE SAVIEZ-VOUS ?'}</div><div class="title">${words(s.title)}</div>`;
  if(s.type=='number') h=`<div class="num">0</div><div class="label">${words(s.label)}</div>`;
  if(s.type=='stamp') h=`<div class="title">${words(s.title)}</div><div class="stamp">${s.stamp}</div>`;
  if(s.type=='rain') h=`<div class="title">${words(s.title)}</div>`+Array.from({length:18},(_,k)=>`<div class="drop">${s.emoji}</div>`).join('');
  if(s.type=='text'||s.type=='end') h=`<div class="title">${words(s.title)}</div>`;
  stage.innerHTML=h;
  bg.style.backgroundImage=s.src?`url(${s.src})`:'none';
  cr.textContent=s.credit||'';
}
function render(t){
  let i=0,t0=0; while(i<D.length-1&&t>=t0+D[i]){t0+=D[i];i++}
  const lt=t-t0, d=D[i], s=S[i];
  if(i!=cur){build(i);cur=i}
  document.getElementById('bar').style.width=(100*t/TOTAL)+'%';
  document.getElementById('b1').style.transform=`translate(${Math.sin(t*.6)*80}px,${Math.cos(t*.5)*60}px)`;
  document.getElementById('b2').style.transform=`translate(${Math.cos(t*.4)*70}px,${Math.sin(t*.7)*50}px)`;
  // fond photo : fondu + zoom lent
  bg.style.opacity=s.src?ease(lt/.6):0; bg.style.transform=`scale(${1.08+lt*.025})`;
  cr.style.opacity=s.src?1:0;
  // sortie de scène
  const out=ease((lt-(d-.35))/.35); stage.style.opacity=1-out; stage.style.transform=`translateX(${-out*120}px)`;
  // mots qui arrivent un par un
  stage.querySelectorAll('.word').forEach((w,k)=>{const p=back((lt-.15-k*.09)/.45);
    w.style.opacity=Math.min(1,Math.max(0,(lt-.15-k*.09)/.25)); w.style.transform=`translateY(${(1-p)*80}px)`});
  const k=stage.querySelector('.kick'); if(k){const p=back(lt/.4);k.style.transform=`scale(${p})`}
  const n=stage.querySelector('.num'); if(n){const p=ease(lt/1.6);n.textContent=Math.round(s.number*p);
    n.style.transform=`scale(${.6+.4*back(lt/.5)})`}
  const st=stage.querySelector('.stamp'); if(st){const p=ease((lt-1)/.25);st.style.opacity=p;
    st.style.transform=`rotate(-12deg) scale(${3-2*p})`}
  stage.querySelectorAll('.drop').forEach((e,j)=>{const x=(j*137)%900, sp=500+(j*53)%400, y=((lt*sp+j*230)%2300)-400;
    e.style.left=x+'px'; e.style.top=(y-1500)+'px'; e.style.transform=`rotate(${(lt*90+j*40)%360}deg)`; e.style.opacity=.9});
  if(s.type=='end'){const p=1+.04*Math.sin(lt*5); stage.querySelector('.title').style.transform=`scale(${p})`}
}
</script></body></html>"""
html = html.replace("__SCENES__", json.dumps(scenes)).replace("__DURS__", json.dumps(durs)).replace("__TOTAL__", str(total))
page_file = os.path.join(tmp, "anim.html")
open(page_file, "w", encoding="utf-8").write(html)

# 3) Rendu image par image -> ffmpeg
frames = int(total * FPS)
silent = os.path.join(tmp, "silent.mp4")
ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS),
                       "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "20", silent],
                      stdin=subprocess.PIPE)
js = """
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: %d, height: %d } });
  await p.goto('file://%s');
  for (let f = 0; f < %d; f++) {
    await p.evaluate(t => render(t), f / %d);
    const buf = await p.screenshot({ type: 'jpeg', quality: 90 });
    const len = Buffer.alloc(4); len.writeUInt32BE(buf.length);
    process.stdout.write(len); process.stdout.write(buf);
  }
  await b.close();
})();
""" % (W, H, page_file, frames, FPS)
node = subprocess.Popen(["node", "-e", js], stdout=subprocess.PIPE, cwd=REPO)
done = 0
while True:
    head = node.stdout.read(4)
    if len(head) < 4:
        break
    ff.stdin.write(node.stdout.read(int.from_bytes(head, "big")))
    done += 1
    if done % 150 == 0:
        print(f"  {done}/{frames} images", flush=True)
node.wait(); ff.stdin.close(); ff.wait()
if node.returncode or ff.returncode:
    sys.exit("Erreur de rendu")

# 4) Assemblage vidéo + voix
out = os.path.join(d, "anim.mp4")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", voice, "-c:v", "copy",
                "-c:a", "aac", "-b:a", "160k", "-shortest", out], check=True)
print(f"{out} ({total:.1f} s)")
