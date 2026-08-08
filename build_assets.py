# -*- coding: utf-8 -*-
"""
Run ONCE locally before pushing to GitHub. Copies the finished PNGs into ./posts/ with
clean ascii names (001.png ...) and writes ./captions_ascii.json keyed by those names.

  python build_assets.py "C:/Users/Acer/Dropbox/أحاديث 14/بوستات جاهزة 200"
"""
import sys, json, shutil, pathlib

HERE = pathlib.Path(__file__).parent
SRC = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else \
      pathlib.Path(r"C:/Users/Acer/Dropbox/أحاديث 14/بوستات جاهزة 200")
POSTS = HERE / "posts"; POSTS.mkdir(exist_ok=True)

master = json.loads((HERE / "captions.json").read_text(encoding="utf-8"))  # {orig_name: {ascii, caption, ...}}
ascii_caps = {}
copied = 0
for orig, meta in master.items():
    src = SRC / orig
    if not src.exists():
        print("[missing]", orig); continue
    dst = POSTS / meta["ascii"]                       # .jpg — 1080x1350 keeps the repo small
    from PIL import Image
    Image.open(src).convert("RGB").resize((1080, 1350), Image.LANCZOS)\
         .save(dst, quality=92, subsampling=0, optimize=True)
    cap = meta["caption"]                             # carry tags across a rebuild, else the
    if not isinstance(cap, dict): cap = {"caption": cap}   # hashtags silently vanish
    ascii_caps[meta["ascii"]] = {**cap, "tags": meta.get("tags", [])}
    copied += 1
(HERE / "captions_ascii.json").write_text(json.dumps(ascii_caps, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"copied {copied} images -> posts/ ; captions_ascii.json written ({len(ascii_caps)})")
