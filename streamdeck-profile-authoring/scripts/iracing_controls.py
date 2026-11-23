#!/usr/bin/env python3
"""Dump the bindings in an iRacing controls.cfg (binary, magic 'GFCC').

usage: iracing_controls.py <controls.cfg> [--all]

Prints one line per action: KEY <combo>, JOY (bound to a device button), AXIS, or '-' (unbound,
only with --all). Layout reverse-engineered from real files (2026 builds); see SKILL.md.
"""
import re, struct, sys

MODS = ((0x30000, "Shift"), (0xC0000, "Ctrl"), (0x300000, "Alt"))
SPECIAL = {32: "Space", 33: "PgUp", 34: "PgDn", 37: "Left", 38: "Up", 39: "Right", 40: "Down",
           45: "Ins", 46: "Del", 107: "Num+", 109: "Num-", 108: "-", 114: "=", 118: "[", 120: "]",
           12: "Num5", 9: "Tab", 44: "PrtScr"}
SPECIAL.update({196 + n: f"F{n}" for n in range(1, 13)})


def key_name(code):
    if code in SPECIAL:
        return SPECIAL[code]
    if 48 <= code <= 57 or 65 <= code <= 90:
        return chr(code)
    return f"#{code}"


def combo(code, mask):
    return "+".join([n for bit, n in MODS if mask & bit == bit] + [key_name(code)])


def records(data):
    # Joystick records end in a product GUID whose last bytes read "PIDVID",
    # which runs straight into the next action name.
    for m in re.finditer(rb"(?:PIDVID)?([A-Z][A-Za-z0-9_]{2,40})\x00", data):
        s = m.end()
        if s + 20 > len(data):
            continue
        a, flags, typ, x, y = struct.unpack_from("<IIIII", data, s)
        if flags in (6, 0x19, 0x1F) and a <= 4:
            yield m.group(1).decode(), s, typ, x, y


def main(path, show_all=False):
    data = open(path, "rb").read()
    assert data[:4] == b"GFCC", "not an iRacing controls.cfg"
    for name, _, typ, x, y in records(data):
        if typ == 4:
            print(f"{name:32} KEY   {combo(x, y)}")
        elif typ == 2:
            # Button index encoding varies between record variants; don't guess it.
            print(f"{name:32} JOY   (wheel / button box / pedals)")
        elif typ == 1:
            print(f"{name:32} AXIS  {x}")
        elif show_all:
            print(f"{name:32} -")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1], "--all" in sys.argv)
