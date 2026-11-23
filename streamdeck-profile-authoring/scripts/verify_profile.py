#!/usr/bin/env python3
"""Sanity-check a generated .streamDeckProfile (V2 or V3) before importing it.

usage: verify_profile.py <file.streamDeckProfile> [cols rows]   (default 5 3)
"""
import io, json, re, sys, zipfile

try:
    from PIL import Image
except ImportError:  # size check is optional
    Image = None


def verify(path, cols=5, rows=3):
    z = zipfile.ZipFile(path)
    names = set(z.namelist())
    assert all("\\" not in n for n in names), "zip entries must use forward slashes"
    top = [n for n in names if n.count("/") == 1 and n.endswith("/manifest.json")]
    assert len(top) == 1, f"expected exactly one <uuid>.sdProfile/manifest.json at the root, got {top}"
    root = top[0].split("/")[0]
    tm = json.loads(z.read(top[0]))
    v3 = str(tm.get("Version", "")).startswith("3")
    pages = {n.split("/")[2] for n in names if n.startswith(root + "/Profiles/") and n.count("/") >= 3}

    def page_dir(u):
        if v3:
            return u.upper()
        raw = u.replace("-", "") + "000"
        out = ""
        for i in range(0, len(raw), 5):
            n = int(raw[i:i + 5], 16); s = ""
            while n:
                s = "0123456789abcdefghijklmnopqrstuv"[n % 32] + s; n //= 32
            out += s.rjust(4, "0")
        return out[:26].upper().replace("V", "W").replace("U", "V") + "Z"

    rootpage = page_dir(tm["Pages"]["Current"])
    assert rootpage in pages, "Pages.Current has no directory"
    for u in tm["Pages"]["Pages"] + [tm["Pages"]["Default"]]:
        assert page_dir(u) in pages, f"page {u} has no directory"

    ids, imgs, keys = set(), set(), 0
    for p in sorted(pages):
        m = json.loads(z.read(f"{root}/Profiles/{p}/manifest.json"))
        acts = m["Controllers"][0]["Actions"] or {}
        backs = 0
        for k, a in acts.items():
            c, r = map(int, k.split(","))
            assert 0 <= c < cols and 0 <= r < rows, f"{p} {k}: outside {cols}x{rows} grid"
            assert a["ActionID"] not in ids, f"duplicate ActionID {a['ActionID']}"
            ids.add(a["ActionID"])
            img = a["States"][0].get("Image", "")
            assert re.fullmatch(r"Images/[0-9A-Z]{26}Z\.png", img), f"{p} {k}: bad Image {img!r}"
            full = f"{root}/Profiles/{p}/{img}"
            assert full in names, f"{p} {k}: missing {img}"
            assert img not in imgs, f"image filename reused: {img}"
            imgs.add(img)
            if Image:
                size = Image.open(io.BytesIO(z.read(full))).size
                assert size == (144, 144), f"{img} is {size}, want 144x144"
            if a["UUID"].endswith("openchild"):
                assert page_dir(a["Settings"]["ProfileUUID"]) in pages, f"{p} {k}: folder target missing"
            if a["UUID"].endswith("backtoparent"):
                backs += 1
            keys += 1
        if acts:
            want = 0 if p == rootpage else 1
            assert backs == want, f"{p}: {backs} back keys, want {want}"
    print(f"OK  {'V3' if v3 else 'V2'}  {len(pages)} page dirs, {keys} keys")


if __name__ == "__main__":
    if len(sys.argv) not in (2, 4):
        sys.exit(__doc__)
    verify(sys.argv[1], *(int(x) for x in sys.argv[2:4]))
