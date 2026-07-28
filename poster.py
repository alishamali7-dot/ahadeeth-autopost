# -*- coding: utf-8 -*-
"""
Ahadeeth__14 auto-poster — posts the next unpublished image to Telegram (and, when
configured, Instagram). Resumable via a ledger; safe to run twice.

Commands:
  python poster.py status                 # queue + how many posted per platform
  python poster.py post-next [--dry-run]  # post the next unpublished image
  python poster.py post-due  [--dry-run]  # same, but only once per 10:00/22:00 Kuwait slot
  python poster.py post 12   [--dry-run]  # post a specific image number
  python poster.py post-next --platform telegram   # limit to one platform
  python poster.py ig-check               # verify the Instagram token / id / public image URL

Config comes from env vars (GitHub Actions secrets) or config.json:
  TELEGRAM_TOKEN, TELEGRAM_CHANNEL   (e.g. @ahadeeth_14)
  IG_TOKEN, IG_USER_ID, PUBLIC_BASE_URL   (Instagram — optional, phase 2)
"""
import os, sys, json, glob, pathlib, datetime

HERE = pathlib.Path(__file__).parent
POSTS_DIR = HERE / "posts"                       # ascii-named images: 001.jpg ...
CAPTIONS  = HERE / "captions_ascii.json"         # { "001.jpg": caption | {caption, extra} }
LEDGER    = HERE / "published.json"              # { "001.png": {"telegram": ISO, "instagram": ISO} }
TG_LIMIT  = 1024                                 # Telegram photo-caption char limit

def cfg(key, default=None):
    # .strip(): secrets pasted with a trailing newline turn into bot<token>%0A/sendPhoto → 404
    if os.environ.get(key): return os.environ[key].strip()
    p = HERE / "config.json"
    if p.exists():
        v = json.loads(p.read_text(encoding="utf-8")).get(key, default)
        return v.strip() if isinstance(v, str) else v
    return default

def load(p, d):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else d

def utc(): return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
def now(): return utc().isoformat(timespec="seconds") + "Z"

SLOTS  = (7, 19)      # UTC hours = 10:00 and 22:00 Kuwait (UTC+3, no DST)
WINDOW = 5            # hours a slot stays claimable — GitHub's cron fires late under load

def due_slot(t):
    """The posting slot t falls into, or None. Cron knocks every 15 min inside the windows;
    whichever run actually fires first claims the slot, so a delayed cron still posts."""
    for h in sorted(SLOTS, reverse=True):
        s = t.replace(hour=h, minute=0, second=0, microsecond=0)
        if s <= t < s + datetime.timedelta(hours=WINDOW): return s
    return None

def slot_taken(ledger, slot):
    stamps = [v[p] for v in ledger.values() for p in v]
    return any(x >= slot.isoformat(timespec="seconds") + "Z" for x in stamps)

def images():
    return sorted(glob.glob(str(POSTS_DIR / "*.jpg")))

def next_unpublished(ledger, platform):
    for img in images():
        name = os.path.basename(img)
        if platform not in ledger.get(name, {}):
            return img
    return None

# ------------------------------------------------------------ Telegram
def parts(entry):
    """A caption is either the whole text, or {caption, extra} when the takhrij is too long
    for Telegram's 1024-char photo caption and has to follow as its own message."""
    if isinstance(entry, dict): return entry.get("caption", ""), entry.get("extra", "")
    return entry or "", ""

def post_telegram(img, entry, dry):
    caption, extra = parts(entry)
    token, chan = cfg("TELEGRAM_TOKEN"), cfg("TELEGRAM_CHANNEL")
    if dry:
        print(f"[DRY] telegram -> {chan or '<no channel set>'}: {os.path.basename(img)} | "
              f"caption {len(caption)} chars | follow-up {len(extra)} chars")
        return True
    if not token or not chan:
        raise SystemExit("Missing TELEGRAM_TOKEN / TELEGRAM_CHANNEL")
    import requests
    api = f"https://api.telegram.org/bot{token}"
    if len(caption) > TG_LIMIT:                       # shouldn't happen — captions are built to fit
        extra, caption = (caption + "\n\n" + extra).strip(), caption.split("\n\n")[0]
    with open(img, "rb") as f:
        r = requests.post(f"{api}/sendPhoto",
                          data={"chat_id": chan, "caption": caption, "parse_mode": "HTML"},
                          files={"photo": f}, timeout=60)
    if not r.ok:                                      # Telegram explains itself in the body
        raise RuntimeError(f"Telegram {r.status_code} for chat {chan!r}: {r.text}")
    ok = r.json().get("ok")
    if ok and extra:                                  # takhrij as a reply under the photo
        mid = r.json()["result"]["message_id"]
        requests.post(f"{api}/sendMessage",
                      data={"chat_id": chan, "text": extra[:4096], "parse_mode": "HTML",
                            "reply_to_message_id": mid}, timeout=60).raise_for_status()
    if not ok: raise RuntimeError(f"Telegram error: {r.text}")
    return True

# ------------------------------------------------------------ Instagram (phase 2)
IG_LIMIT = 2200                                   # Instagram caption limit

def ig_caption(entry):
    caption, extra = parts(entry)
    text = (caption + ("\n\n" + extra if extra else "")).replace("<b>", "").replace("</b>", "")
    if len(text) <= IG_LIMIT: return text
    cut = text.rfind("\n", 0, IG_LIMIT - 1)        # drop whole trailing lines, never mid-word
    return text[:cut].rstrip() + " …"

def graph(method, path, **data):
    import requests
    r = getattr(requests, method)(f"https://graph.facebook.com/v21.0/{path}",
                                  data=data if method == "post" else None,
                                  params=None if method == "post" else data, timeout=120)
    if not r.ok:                                   # Meta puts the real reason in the body
        raise RuntimeError(f"Instagram {r.status_code} on {path}: {r.text}")
    return r.json()

def post_instagram(img, entry, dry):
    token, uid, base = cfg("IG_TOKEN"), cfg("IG_USER_ID"), cfg("PUBLIC_BASE_URL")
    if not (token and uid and base):
        print("[skip] Instagram not configured (IG_TOKEN/IG_USER_ID/PUBLIC_BASE_URL)"); return False
    caption = ig_caption(entry)
    image_url = base.rstrip("/") + "/posts/" + os.path.basename(img)   # must be publicly reachable
    if dry:
        print(f"[DRY] instagram -> {uid}: {image_url} | caption {len(caption)} chars"); return True
    cid = graph("post", f"{uid}/media", image_url=image_url, caption=caption, access_token=token)["id"]
    graph("post", f"{uid}/media_publish", creation_id=cid, access_token=token)
    return True

PLATFORMS = {"telegram": post_telegram, "instagram": post_instagram}

def do_post(img, dry, only=None):
    name = os.path.basename(img)
    caps = load(CAPTIONS, {}); ledger = load(LEDGER, {})
    caption = caps.get(name, "")
    targets = [only] if only else list(PLATFORMS)
    failed = []
    for plat in targets:
        if plat in ledger.get(name, {}):
            print(f"[skip] {name} already on {plat}"); continue
        try:
            if PLATFORMS[plat](img, caption, dry) and not dry:
                ledger.setdefault(name, {})[plat] = now()
                print(f"[ok] {name} -> {plat}")
        except Exception as e:                      # one platform failing must not lose the other's
            print(f"[FAIL] {name} -> {plat}: {e}"); failed.append(plat)
    if not dry:                                     # always record what did go out, then report
        LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=1), encoding="utf-8")
    return failed

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
    elif cmd == "ig-check":                         # verify the Instagram side before scheduling it
        token, uid, base = cfg("IG_TOKEN"), cfg("IG_USER_ID"), cfg("PUBLIC_BASE_URL")
        if not token: raise SystemExit("Set IG_TOKEN first (env var or config.json)")
        if not uid:                                 # discover it from the linked Facebook page
            pages = graph("get", "me/accounts", access_token=token, fields="name,id").get("data", [])
            for p in pages:
                d = graph("get", p["id"], access_token=token, fields="instagram_business_account{id,username}")
                print(f"page {p['name']} ({p['id']}) -> {d.get('instagram_business_account')}")
            if not pages: print("no Facebook pages on this token")
            return
        me = graph("get", uid, access_token=token, fields="username,followers_count,media_count")
        print("instagram:", me)
        if base:
            import requests
            u = base.rstrip("/") + "/posts/" + os.path.basename(images()[0])
            r = requests.head(u, timeout=30, allow_redirects=True)
            print(f"image url {u} -> HTTP {r.status_code}"
                  f"{' (must be 200 and public)' if r.status_code != 200 else ''}")
        else:
            print("PUBLIC_BASE_URL not set — Instagram needs a public https URL for each image")
    elif cmd in ("post-next", "post-due"):
        ledger = load(LEDGER, {})
        if cmd == "post-due":                       # scheduled path: post once per slot
            t = utc()
            slot = due_slot(t)
            if not slot:
                print(f"[skip] {t:%H:%M} UTC is outside a posting window {SLOTS}"); return
            if slot_taken(ledger, slot):
                print(f"[skip] the {slot:%H:%M}Z slot already has its post"); return
        img = next_unpublished(ledger, only or "telegram")
        if not img: print("Nothing left to post."); return
        if do_post(img, dry, only): sys.exit(1)     # red run when a platform refused
    elif cmd == "post":
        num = f"{int(args[1]):03d}.jpg"; img = str(POSTS_DIR / num)
        if not os.path.exists(img): raise SystemExit(f"No such image {num}")
        if do_post(img, dry, only): sys.exit(1)
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
