#!/usr/bin/env python3
"""Publie un post (image seule ou carrousel) sur Instagram @lessentiel.befr.

Usage : python3 tools/publish.py posts/<dossier>
Le dossier contient slide-1.jpg ... slide-N.jpg et caption.txt.
Étapes : push des images sur GitHub (hébergement public) -> conteneurs Instagram -> publication.
Le token Meta est injecté automatiquement par le proxy réseau pour graph.facebook.com.
"""
import json, subprocess, sys, time, glob, os

IG_USER = "17841431178479839"
GRAPH = "https://graph.facebook.com/v21.0"
RAW = "https://raw.githubusercontent.com/hormalaroussi2-boop/lessentiel-images/main"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sh(*args):
    return subprocess.run(args, cwd=REPO, check=True, capture_output=True, text=True).stdout


def graph(method, path, **params):
    cmd = ["curl", "-sS", "--max-time", "120"]
    if method == "POST":
        cmd += ["-X", "POST"]
        for k, v in params.items():
            cmd += ["--data-urlencode", f"{k}={v}"]
        url = f"{GRAPH}/{path}"
    else:
        cmd += ["-G"] + sum([["--data-urlencode", f"{k}={v}"] for k, v in params.items()], [])
        url = f"{GRAPH}/{path}"
    out = subprocess.run(cmd + [url], capture_output=True, text=True).stdout
    data = json.loads(out or "{}")
    if "error" in data:
        raise RuntimeError(f"{path}: {data['error'].get('message')}")
    return data


def retry(fn, tries=6, wait=10):
    for i in range(tries):
        try:
            return fn()
        except RuntimeError as e:
            if i == tries - 1:
                raise
            print(f"  nouvel essai dans {wait}s ({e})")
            time.sleep(wait)


def wait_ready(cid):
    for _ in range(30):
        st = graph("GET", cid, fields="status_code").get("status_code")
        if st == "FINISHED":
            return
        if st == "ERROR":
            raise RuntimeError(f"conteneur {cid} en erreur")
        time.sleep(5)
    raise RuntimeError(f"conteneur {cid} pas prêt")


def main():
    post_dir = os.path.relpath(os.path.abspath(sys.argv[1]), REPO)
    images = sorted(glob.glob(os.path.join(REPO, post_dir, "slide-*.jpg")),
                    key=lambda p: int(p.rsplit("-", 1)[1].split(".")[0]))
    caption = open(os.path.join(REPO, post_dir, "caption.txt"), encoding="utf-8").read().strip()
    if not images or len(images) > 10:
        sys.exit(f"Il faut entre 1 et 10 images (trouvé {len(images)}).")
    if len(caption) > 2200:
        sys.exit("Légende trop longue (max 2200 caractères).")

    # 1. Hébergement public sur GitHub
    sh("git", "add", post_dir)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=REPO).returncode:
        sh("git", "-c", "user.name=Claude", "-c", "user.email=noreply@anthropic.com",
           "commit", "-qm", f"Post {post_dir}")
    sh("git", "pull", "-q", "--rebase", "origin", "main")
    sh("git", "push", "-q", "origin", "main")
    urls = [f"{RAW}/{post_dir}/{os.path.basename(p)}" for p in images]
    time.sleep(5)

    # 2. Conteneurs Instagram
    if len(urls) == 1:
        cid = retry(lambda: graph("POST", f"{IG_USER}/media", image_url=urls[0], caption=caption))["id"]
    else:
        children = []
        for u in urls:
            c = retry(lambda u=u: graph("POST", f"{IG_USER}/media", image_url=u, is_carousel_item="true"))["id"]
            children.append(c)
            print("  image ok", c)
        for c in children:
            wait_ready(c)
        cid = retry(lambda: graph("POST", f"{IG_USER}/media", media_type="CAROUSEL",
                                  children=",".join(children), caption=caption))["id"]
    wait_ready(cid)

    # 3. Publication
    media_id = retry(lambda: graph("POST", f"{IG_USER}/media_publish", creation_id=cid))["id"]
    link = graph("GET", media_id, fields="permalink").get("permalink")
    print("PUBLIÉ :", link)
    with open(os.path.join(REPO, post_dir, "published.txt"), "w") as f:
        f.write(f"{media_id}\n{link}\n")


if __name__ == "__main__":
    main()
