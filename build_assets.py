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
    dst = POSTS / meta["ascii"]
    shutil.copyfile(src, dst)
    ascii_caps[meta["ascii"]] = meta["caption"]
    copied += 1
(HERE / "captions_ascii.json").write_text(json.dumps(ascii_caps, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"copied {copied} images -> posts/ ; captions_ascii.json written ({len(ascii_caps)})")
