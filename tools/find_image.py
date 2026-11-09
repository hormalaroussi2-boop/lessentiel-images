#!/usr/bin/env python3
"""Cherche une vraie photo sous licence libre sur Wikimedia Commons et la télécharge.

Usage :
  python3 tools/find_image.py "Parlement fédéral belge"            -> liste 8 candidats
  python3 tools/find_image.py "Parlement fédéral belge" <dossier> 2 -> télécharge le candidat n°2
                                                                     dans <dossier>/img-<n>.jpg
Affiche le crédit à recopier dans post.json ("credit").
Seules les licences libres réutilisables (CC0, domaine public, CC BY, CC BY-SA) sont gardées.
"""
import json, re, subprocess, sys, os, html, urllib.parse

API = "https://commons.wikimedia.org/w/api.php"
UA = "LEssentielBeFr/1.0 (https://www.instagram.com/lessentiel.befr/)"
OK = re.compile(r"^(cc0|public domain|pd|cc by(-sa)? [0-9.]+|cc by(-sa)?)", re.I)


def get(url, out=None):
    cmd = ["curl", "-sSL", "--max-time", "60", "-A", UA, url]
    if out:
        subprocess.run(cmd + ["-o", out], check=True)
        return None
    import time
    for wait in (5, 15, 30, 60, None):
        out = subprocess.run(cmd, capture_output=True, text=True).stdout
        try:
            return json.loads(out)
        except json.JSONDecodeError:
            if wait is None:
                sys.exit(f"Wikimedia ne répond pas (limite de requêtes ?) : {out[:120]}")
            time.sleep(wait)


def clean(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def search(q):
    params = {"action": "query", "format": "json", "generator": "search", "gsrsearch": f"{q} filetype:bitmap",
              "gsrnamespace": 6, "gsrlimit": 25, "prop": "imageinfo",
              "iiprop": "url|extmetadata|size", "iiurlwidth": 1280}
    pages = get(API + "?" + urllib.parse.urlencode(params)).get("query", {}).get("pages", {})
    res = []
    for p in sorted(pages.values(), key=lambda p: p.get("index", 0)):
        ii = p["imageinfo"][0]
        m = ii.get("extmetadata", {})
        lic = clean(m.get("LicenseShortName", {}).get("value"))
        if not OK.match(lic) or ii.get("width", 0) < 900:
            continue
        artist = clean(m.get("Artist", {}).get("value")) or "auteur inconnu"
        # Miniature de taille standard (1280 px) servie par upload.wikimedia.org : les originaux
        # et les tailles non standard sont limités par Wikimedia (erreur 429).
        url = (ii.get("thumburl") or ii["url"]).split("?")[0].replace("//thumb.wikimedia.org/", "//upload.wikimedia.org/")
        res.append({"title": p["title"], "url": url,
                    "credit": f"Photo : {artist[:60]} / Wikimedia Commons ({lic})"})
    return res[:8]


if __name__ == "__main__":
    q = sys.argv[1]
    res = search(q)
    if len(sys.argv) < 4:
        for i, r in enumerate(res, 1):
            print(f"{i}. {r['title']}\n   {r['credit']}")
        if not res:
            print("Aucune image libre trouvée : essaie un autre mot-clé (lieu, objet, personne).")
        sys.exit(0)
    d, n = sys.argv[2], int(sys.argv[3])
    r = res[n - 1]
    existing = [f for f in os.listdir(d) if f.startswith("img-") and f.endswith(".jpg")]
    out = os.path.join(d, f"img-{len(existing) + 1}.jpg")
    get(r["url"], out + ".orig")
    from PIL import Image
    im = Image.open(out + ".orig").convert("RGB")
    im.thumbnail((1600, 1600))
    im.save(out, quality=88)
    os.remove(out + ".orig")
    print(json.dumps({"image": os.path.basename(out), "credit": r["credit"]}, ensure_ascii=False))
