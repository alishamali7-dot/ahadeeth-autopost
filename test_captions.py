# -*- coding: utf-8 -*-
"""Guards the hashtag wiring. Run after editing captions or poster.py:

    python test_captions.py
"""
import json, re, pathlib, importlib.util

HERE = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location("poster", HERE / "poster.py")
p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)

caps = json.loads((HERE / "captions_ascii.json").read_text(encoding="utf-8"))
assert caps, "captions_ascii.json is empty"

for name, entry in caps.items():
    ig, tags = p.ig_caption(entry), p.tagline(entry)
    body, extra = p.parts(entry)

    assert tags in ig, f"{name}: Instagram caption lost its hashtags"
    assert len(ig) <= p.IG_LIMIT, f"{name}: Instagram caption {len(ig)} > {p.IG_LIMIT}"
    # @ahadeeth_14 is the Telegram channel; on Instagram it would mention a foreign account.
    assert "@ahadeeth_14" not in ig, f"{name}: Telegram handle leaked into Instagram caption"
    # Tags live in entry["tags"], never inline in the text, or they get appended twice.
    assert len(re.findall(r"#أحاديث_14\b", ig)) == 1, f"{name}: duplicated tagline"
    assert "#أحاديث" not in body + str(extra), f"{name}: inline hashtags left in caption text"

print(f"OK: {len(caps)} captions — hashtags present once, within limits, right handle per platform")
