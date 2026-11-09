// Génère les images d'un post (carrousel style journal) à partir d'un post.json.
// Usage : node tools/render.js posts/<dossier>
// post.json : { "date": "LUNDI 9 NOVEMBRE 2026", "edition": "MATIN" | "APRÈS-MIDI" | "URGENT",
//   "slides": [
//     { "type": "cover", "items": [["ARGENT", "Titre court"], ...] },
//     { "type": "story", "tag": "ARGENT", "country": "FRANCE", "title": "...", "body": "... <b>mot clé</b> ...", "source": "franceinfo, Le Monde" },
//     { "type": "end", "question": "Et vous, ... ?" }
//   ] }
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const dir = process.argv[2];
if (!dir) { console.error('Usage: node tools/render.js <dossier du post>'); process.exit(1); }
const post = JSON.parse(fs.readFileSync(path.join(dir, 'post.json'), 'utf8'));
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/&lt;b&gt;/g, '<b>').replace(/&lt;\/b&gt;/g, '</b>');
const N = post.slides.length;
const urgent = post.edition === 'URGENT';
const head = `<div class="mast"><div class="brand">L'ESSENTIEL${urgent ? ' <span class="urg">URGENT</span>' : ''}</div><div class="date">${esc(post.date)}</div></div>`;
const foot = (n) => `<div class="foot"><span>@LESSENTIEL.BEFR</span><span>${N > 1 ? `${n}/${N}` : 'BELGIQUE · FRANCE'}</span></div>`;

function slide(s, i) {
  const n = i + 1;
  if (s.type === 'cover') {
    const ed = post.edition === 'APRÈS-MIDI' ? "de l'après-midi" : post.edition === 'MATIN' ? 'du matin' : 'du jour';
    return `${head}<div class="kicker">ÉDITION BELGIQUE · FRANCE</div>
<h1 class="big">L'essentiel<br>${ed}</h1><div class="rule"></div>
<ul>${s.items.map(([t, x]) => `<li><b>${esc(t)}</b><span>${esc(x)}</span></li>`).join('')}</ul>
${N > 1 ? '<div class="swipe">Faites défiler →</div>' : ''}${foot(n)}`;
  }
  if (s.type === 'story') {
    return `${head}<div class="tag">${esc(s.tag)}<span class="ctry">${esc(s.country)}</span></div>
<h1>${esc(s.title)}</h1><div class="rule"></div><p>${esc(s.body)}</p>
<div class="src">Source : ${esc(s.source)}</div>${foot(n)}`;
  }
  if (s.type === 'end') {
    return `${head}<div class="q">Et vous ?</div><h1 class="big2">${esc(s.question)}</h1><div class="rule"></div>
<p class="cta">Répondez en commentaire</p><div class="follow">ABONNEZ-VOUS<br><span>l'essentiel à 11h et 16h, chaque jour</span></div>${foot(n)}`;
  }
  throw new Error('type de slide inconnu : ' + s.type);
}

const css = `*{margin:0;box-sizing:border-box}body{width:1080px;height:1350px;background:#f4efe4;font-family:'DejaVu Serif',serif;color:#141414;padding:70px 80px;position:relative;overflow:hidden}
.mast{border-top:10px solid #141414;border-bottom:3px solid #141414;padding:22px 0 18px;display:flex;justify-content:space-between;align-items:baseline}
.brand{font-family:'Inter';font-weight:900;font-size:40px;letter-spacing:2px}.urg{background:#b3261e;color:#fff;padding:2px 12px;margin-left:8px}
.date{font-family:'Inter';font-weight:600;font-size:24px;color:#b3261e}
.tag{margin-top:70px;display:inline-block;background:#b3261e;color:#fff;font-family:'Inter';font-weight:800;font-size:30px;letter-spacing:3px;padding:12px 24px}
.ctry{background:#141414;margin-left:24px;padding:12px 24px;margin-right:-24px}
h1{font-size:72px;line-height:1.08;margin-top:40px;font-weight:700}.rule{width:160px;height:8px;background:#b3261e;margin:40px 0}
p{font-size:38px;line-height:1.42;color:#2a2a2a}b{color:#b3261e}
.src{position:absolute;bottom:140px;left:80px;right:80px;font-family:'Inter';font-size:24px;color:#6b6b6b;font-style:italic}
.foot{position:absolute;bottom:70px;left:80px;right:80px;border-top:3px solid #141414;padding-top:20px;display:flex;justify-content:space-between;font-family:'Inter';font-weight:700;font-size:24px;letter-spacing:3px}
.kicker{margin-top:90px;font-family:'Inter';font-weight:800;color:#b3261e;font-size:30px;letter-spacing:4px}.big{font-size:130px;line-height:1;margin-top:30px}
ul{list-style:none}li{font-size:36px;padding:16px 0;border-bottom:1px solid #c9c1b0;display:flex;align-items:baseline}li b{flex:0 0 250px;font-family:'Inter';font-weight:800;font-size:26px;letter-spacing:2px;color:#b3261e}
.swipe{position:absolute;bottom:160px;right:80px;font-family:'Inter';font-weight:700;font-size:30px}
.q{margin-top:150px;font-size:60px;font-style:italic;color:#b3261e}.big2{font-size:88px}.cta{font-family:'Inter';font-weight:600}
.follow{position:absolute;bottom:170px;left:80px;right:80px;background:#141414;color:#f4efe4;text-align:center;padding:36px;font-family:'Inter';font-weight:900;font-size:50px;letter-spacing:4px}.follow span{font-weight:500;font-size:28px;letter-spacing:1px}`;

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1350 } });
  for (const [i, s] of post.slides.entries()) {
    await page.setContent(`<html><head><meta charset="utf-8"><style>${css}</style></head><body>${slide(s, i)}</body></html>`);
    // Vérifie que le texte ne déborde pas sur la source / le pied de page.
    const overflow = await page.evaluate(() => {
      const p = document.querySelector('p:not(.cta)'), src = document.querySelector('.src');
      return p && src ? p.getBoundingClientRect().bottom > src.getBoundingClientRect().top - 10 : false;
    });
    if (overflow) console.warn(`ATTENTION slide ${i + 1} : le texte déborde, raccourcis-le.`);
    const out = path.join(dir, `slide-${i + 1}.jpg`);
    await page.screenshot({ path: out, type: 'jpeg', quality: 90 });
    console.log(out);
  }
  await browser.close();
})();
