# -*- coding: utf-8 -*-
"""
Ahadeeth__14 auto-poster — posts the next unpublished image to Telegram (and, when
configured, Instagram). Resumable via a ledger; safe to run twice.

Commands:
  python poster.py status                 # queue + how many posted per platform
  python poster.py post-next [--dry-run]  # post the next unpublished image
  python poster.py post 12   [--dry-run]  # post a specific image number
  python poster.py post-next --platform telegram   # limit to one platform

Config comes from env vars (GitHub Actions secrets) or config.json:
  TELEGRAM_TOKEN, TELEGRAM_CHANNEL   (e.g. @ahadeeth_14)
  IG_TOKEN, IG_USER_ID, PUBLIC_BASE_URL   (Instagram — optional, phase 2)
"""
import os, sys, json, glob, pathlib, datetime

HERE = pathlib.Path(__file__).parent
POSTS_DIR = HERE / "posts"                       # ascii-named images: 001.png ...
CAPTIONS  = HERE / "captions_ascii.json"         # { "001.png": "caption text", ... }
LEDGER    = HERE / "published.json"              # { "001.png": {"telegram": ISO, "instagram": ISO} }
TG_LIMIT  = 1024                                 # Telegram photo-caption char limit

def cfg(key, default=None):
    if os.environ.get(key): return os.environ[key]
    p = HERE / "config.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8")).get(key, default)
    return default

def load(p, d):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else d

def now(): return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"

def images():
    return sorted(glob.glob(str(POSTS_DIR / "*.png")))

def next_unpublished(ledger, platform):
    for img in images():
        name = os.path.basename(img)
        if platform not in ledger.get(name, {}):
            return img
    return None

# ------------------------------------------------------------ Telegram
def post_telegram(img, caption, dry):
    token, chan = cfg("TELEGRAM_TOKEN"), cfg("TELEGRAM_CHANNEL")
    if dry:
        print(f"[DRY] telegram -> {chan or '<no channel set>'}: {os.path.basename(img)} | caption {len(caption)} chars")
        return True
    if not token or not chan:
        raise SystemExit("Missing TELEGRAM_TOKEN / TELEGRAM_CHANNEL")
    import requests
    api = f"https://api.telegram.org/bot{token}"
    with open(img, "rb") as f:
        if len(caption) <= TG_LIMIT:
            r = requests.post(f"{api}/sendPhoto",
                              data={"chat_id": chan, "caption": caption}, files={"photo": f}, timeout=60)
        else:
            r = requests.post(f"{api}/sendPhoto", data={"chat_id": chan}, files={"photo": f}, timeout=60)
    r.raise_for_status(); ok = r.json().get("ok")
    if ok and len(caption) > TG_LIMIT:                # long text as a follow-up message
        requests.post(f"{api}/sendMessage",
                      data={"chat_id": chan, "text": caption[:4096]}, timeout=60).raise_for_status()
    if not ok: raise SystemExit(f"Telegram error: {r.text}")
    return True

# ------------------------------------------------------------ Instagram (phase 2)
def post_instagram(img, caption, dry):
    token, uid, base = cfg("IG_TOKEN"), cfg("IG_USER_ID"), cfg("PUBLIC_BASE_URL")
    if not (token and uid and base):
        print("[skip] Instagram not configured (IG_TOKEN/IG_USER_ID/PUBLIC_BASE_URL)"); return False
    image_url = base.rstrip("/") + "/posts/" + os.path.basename(img)   # public raw URL
    if dry:
        print(f"[DRY] instagram -> {uid}: {image_url}"); return True
    import requests
    g = "https://graph.facebook.com/v19.0"
    c = requests.post(f"{g}/{uid}/media",
                      data={"image_url": image_url, "caption": caption, "access_token": token}, timeout=120)
    c.raise_for_status(); cid = c.json()["id"]
    p = requests.post(f"{g}/{uid}/media_publish",
                      data={"creation_id": cid, "access_token": token}, timeout=120)
    p.raise_for_status(); return True

PLATFORMS = {"telegram": post_telegram, "instagram": post_instagram}

def do_post(img, dry, only=None):
    name = os.path.basename(img)
    caps = load(CAPTIONS, {}); ledger = load(LEDGER, {})
    caption = caps.get(name, "")
    targets = [only] if only else list(PLATFORMS)
    for plat in targets:
        if plat in ledger.get(name, {}):
            print(f"[skip] {name} already on {plat}"); continue
        try:
            if PLATFORMS[plat](img, caption, dry) and not dry:
                ledger.setdefault(name, {})[plat] = now()
                print(f"[ok] {name} -> {plat}")
        except Exception as e:
            print(f"[FAIL] {name} -> {plat}: {e}")
    if not dry:
        LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=1), encoding="utf-8")

def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    only = None
    if "--platform" in args: only = args[args.index("--platform") + 1]
    cmd = args[0] if args else "status"
    if cmd == "status":
        ledger = load(LEDGER, {}); imgs = images()
        tg = sum("telegram" in v for v in ledger.values())
        ig = sum("instagram" in v for v in ledger.values())
        print(f"images: {len(imgs)} | telegram posted: {tg} | instagram posted: {ig}")
        nxt = next_unpublished(ledger, only or "telegram")
        print("next:", os.path.basename(nxt) if nxt else "— none left —")
    elif cmd == "post-next":
        img = next_unpublished(load(LEDGER, {}), only or "telegram")
        if not img: print("Nothing left to post."); return
        do_post(img, dry, only)
    elif cmd == "post":
        num = f"{int(args[1]):03d}.png"; img = str(POSTS_DIR / num)
        if not os.path.exists(img): raise SystemExit(f"No such image {num}")
        do_post(img, dry, only)
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
