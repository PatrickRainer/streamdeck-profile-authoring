"""Generate iRacing.streamDeckProfile

FOV / horizon / seat height use Ctrl+Shift+1..6: bind those in iRacing
(DCamFOVInc/Dec, DCamVanishYInc/Dec, DCamDrvHeightInc/Dec). Other unbound actions
use Ctrl+Shift+F-keys and Ctrl+Alt+F-keys; see the `NEW` markers in PAGES.
 for Stream Deck MK.2 (5x3), Stream Deck 7.x (V3 layout).

Run:  python3 build_iracing_profile.py [output.streamDeckProfile]
Edit LAYOUT below to move keys; re-run to rebuild.
"""
import io, json, sys, uuid, zipfile
import cairosvg

MODEL = "20GBA9901"                       # Stream Deck MK.2
DEVICE_UUID = None                         # optional: copy "Device.UUID" from one of your installed profiles
APP = "C:\\Program Files (x86)\\iRacing\\iRacingSim64DX11.exe"   # adjust to your install

# ---------------------------------------------------------------- key codes
# (VKey, scan/native, Qt)
def letter(c): return (ord(c), {'A':30,'B':48,'C':46,'D':32,'E':18,'F':33,'G':34,'H':35,'I':23,'J':36,'K':37,'L':38,'M':50,'N':49,'O':24,'P':25,'Q':16,'R':19,'S':31,'T':20,'U':22,'V':47,'W':17,'X':45,'Y':21,'Z':44}[c], ord(c))
def fkey(n): return (111 + n, [59,60,61,62,63,64,65,66,67,68,87,88][n-1], 16777263 + n)
KEYS = {
    "I": letter("I"), "F": letter("F"), "P": letter("P"), "S": letter("S"), "W": letter("W"), "T": letter("T"), "M": letter("M"),
    "Y": letter("Y"), "Z": letter("Z"), "X": letter("X"), "L": letter("L"), "R": letter("R"),
    "A": letter("A"), "V": letter("V"),
    # iRacing defaults ] and [ sit on the physical keys right of P.
    # Swiss-German layout: those are ¨ (VK_OEM_3) and ü (VK_OEM_1).
    "]": (192, 27, 168), "[": (186, 26, 220),
    "PGUP": (33, 73, 16777238), "PGDN": (34, 81, 16777239), "SPACE": (32, 57, 32),
}
for n in range(1, 13): KEYS[f"F{n}"] = fkey(n)
for i, ch in enumerate("1234567890"): KEYS[ch] = (ord(ch), i + 2, ord(ch))

def hotkey(key, ctrl=False, shift=False, alt=False):
    vk, nat, qt = KEYS[key]
    mods = (1 if shift else 0) | (2 if ctrl else 0) | (4 if alt else 0)
    return {"Hotkeys": [
        {"KeyCmd": False, "KeyCtrl": ctrl, "KeyModifiers": mods, "KeyOption": alt, "KeyShift": shift,
         "NativeCode": nat, "QTKeyCode": qt, "VKeyCode": vk},
        {"KeyCmd": False, "KeyCtrl": False, "KeyModifiers": 0, "KeyOption": False, "KeyShift": False,
         "NativeCode": 146, "QTKeyCode": 33554431, "VKeyCode": -1}]}

def combo_text(key, ctrl=False, shift=False, alt=False):
    disp = {"]": "¨-Taste", "[": "Ü-Taste", "PGUP": "PgUp", "PGDN": "PgDn", "SPACE": "Space"}.get(key, key)
    return "+".join([m for m, on in (("Ctrl", ctrl), ("Shift", shift), ("Alt", alt)) if on] + [disp])

# ---------------------------------------------------------------- icons
C = {"endu": "#ffd54f", "car": "#f5a623", "view": "#4fc3f7", "ffb": "#ff5252", "audio": "#66bb6a", "hud": "#b388ff", "nav": "#9e9e9e"}

G = {  # glyphs drawn in a 60x60 box, stroke = currentColor
 "key":   '<circle cx="20" cy="30" r="11"/><circle cx="20" cy="30" r="4"/><path d="M31 30h24M47 30v8M53 30v6"/>',
 "power": '<path d="M30 8v20"/><path d="M18 16a18 18 0 1 0 24 0"/>',
 "wiper": '<path d="M6 46a26 26 0 0 1 48 0"/><path d="M30 50L14 22" stroke-width="6"/><circle cx="30" cy="50" r="3"/>',
 "visor": '<path d="M8 36c0-16 10-26 24-26s20 8 20 18v8z"/><path d="M14 36h38v8H14z"/><path d="M40 18l10 10"/>',
 "light": '<path d="M26 14c-10 0-14 8-14 16s4 16 14 16z"/><path d="M34 18h20M34 30h22M34 42h20"/>',
 "fov":   '<path d="M4 30c8-12 18-18 26-18s18 6 26 18c-8 12-18 18-26 18S12 42 4 30z"/><circle cx="30" cy="30" r="8"/>',
 "seat":  '<path d="M18 6v30h22l6 18"/><path d="M18 36h-4"/><path d="M14 50h26"/>',
 "wheel": '<circle cx="30" cy="30" r="22"/><circle cx="30" cy="30" r="5"/><path d="M8 28h17M35 28h17M30 35v17"/>',
 "folder":'<path d="M6 16h18l5 6h25v28H6z"/>',
 "back":  '<path d="M38 12L18 30l20 18"/>',
 "horizon":'<path d="M4 38h52"/><path d="M14 38a16 16 0 0 1 32 0"/>',
 "cam":   '<rect x="6" y="18" width="36" height="26" rx="4"/><path d="M42 26l12-6v22l-12-6z"/>',
 "mirror":'<rect x="6" y="18" width="48" height="20" rx="8"/><path d="M30 38v10"/>',
 "recenter":'<circle cx="30" cy="30" r="16"/><path d="M30 6v12M30 42v12M6 30h12M42 30h12"/>',
 "look":  '<circle cx="30" cy="30" r="20"/><circle cx="30" cy="30" r="6"/>',
 "eyeoff":'<path d="M4 30c8-12 18-18 26-18s18 6 26 18c-8 12-18 18-26 18S12 42 4 30z"/><path d="M10 52L50 8"/>',
 "zoom":  '<circle cx="26" cy="26" r="16"/><path d="M38 38l16 16"/>',
 "speaker":'<path d="M8 22h10l14-12v40L18 38H8z"/>',
 "headset":'<path d="M10 36v-6a20 20 0 0 1 40 0v6"/><rect x="6" y="34" width="10" height="16" rx="3"/><rect x="44" y="34" width="10" height="16" rx="3"/>',
 "mic":   '<rect x="22" y="6" width="16" height="28" rx="8"/><path d="M14 28a16 16 0 0 0 32 0M30 44v10"/>',
 "sub":   '<rect x="10" y="6" width="40" height="48" rx="4"/><circle cx="30" cy="34" r="12"/><circle cx="30" cy="34" r="4"/><circle cx="30" cy="14" r="3"/>',
 "line":  '<path d="M10 54C10 30 50 34 50 6" stroke-dasharray="6 5"/>',
 "radar": '<path d="M30 52L10 22a26 26 0 0 1 40 0z"/><path d="M18 34a16 16 0 0 1 24 0"/><circle cx="30" cy="46" r="3"/>',
 "fuel":  '<rect x="10" y="10" width="26" height="42" rx="3"/><path d="M14 16h18v12H14zM36 22h8v22a4 4 0 0 0 8 0V18l-6-6"/>',
 "flag":  '<path d="M14 54V8"/><path d="M14 10h32l-6 10 6 10H14"/>',
 "pit":   '<rect x="10" y="8" width="40" height="44" rx="4"/><path d="M18 20h24M18 30h24M18 40h14"/>',
 "marker":'<path d="M30 54S12 34 12 22a18 18 0 0 1 36 0c0 12-18 32-18 32z"/><circle cx="30" cy="22" r="6"/>',
 "shot":  '<rect x="6" y="16" width="48" height="34" rx="5"/><circle cx="30" cy="33" r="10"/><path d="M20 16l4-6h12l4 6"/>',
 "video": '<circle cx="30" cy="30" r="22"/><circle cx="30" cy="30" r="9" fill="currentColor"/>',
 "tire":  '<circle cx="30" cy="30" r="24"/><circle cx="30" cy="30" r="10"/><path d="M30 6v8M30 46v8M6 30h8M46 30h8"/>',
 "wrench":'<path d="M40 6a12 12 0 0 0-10 18L8 46l6 6 22-22a12 12 0 0 0 18-10l-8 6-6-6 6-8z"/>',
 "chat":  '<path d="M8 10h44v30H26l-12 10V40H8z"/>',
 "clear": '<rect x="10" y="10" width="40" height="40" rx="6"/><path d="M20 20l20 20M40 20L20 40"/>',
 "paint": '<path d="M12 48c0-8 6-10 10-6s2 12-10 6z"/><path d="M24 38L48 10l4 4-26 26"/>',
}
BADGE = {  # small overlay in the glyph's top-right
 "+": '<path d="M48 4v16M40 12h16" stroke-width="5"/>', "-": '<path d="M40 12h16" stroke-width="5"/>',
 "up": '<path d="M48 22V4M40 11l8-8 8 8" stroke-width="4"/>', "down": '<path d="M48 4v18M40 15l8 8 8-8" stroke-width="4"/>',
 "left": '<path d="M56 12H38M45 4l-8 8 8 8" stroke-width="4"/>', "right": '<path d="M38 12h18M49 4l8 8-8 8" stroke-width="4"/>',
 "x": '<path d="M40 4l16 16M56 4L40 20" stroke-width="5"/>', "A": '<text x="48" y="20" font-size="18" font-weight="bold" text-anchor="middle" fill="currentColor" stroke="none" font-family="DejaVu Sans">A</text>',
}

def esc(s): return s.replace("&", "&amp;").replace("<", "&lt;")

def icon_png(glyph, color, label, hint, badge=None):
    g = G[glyph] + (BADGE[badge] if badge else "")
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="144" height="144" viewBox="0 0 144 144">
<rect width="144" height="144" fill="#121820"/><rect width="144" height="6" fill="{color}"/>
<g transform="translate(42,14)" fill="none" stroke="{color}" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" color="{color}">{g}</g>
<text x="72" y="104" font-family="DejaVu Sans" font-weight="bold" font-size="{18 if len(label) <= 10 else 15}" fill="#f2f2f2" text-anchor="middle">{esc(label)}</text>
<text x="72" y="128" font-family="DejaVu Sans" font-weight="bold" font-size="13" fill="#8a96a3" text-anchor="middle">{esc(hint)}</text>
</svg>'''
    return cairosvg.svg2png(bytestring=svg.encode(), output_width=144, output_height=144)

# ---------------------------------------------------------------- ids
def encoded_id(u: str) -> str:
    raw = u.replace("-", "") + "000"
    out = ""
    for i in range(0, len(raw), 5):
        n = int(raw[i:i + 5], 16); s = ""
        while n:
            s = "0123456789abcdefghijklmnopqrstuv"[n % 32] + s; n //= 32
        out += s.rjust(4, "0")
    return out[:26].upper().replace("V", "W").replace("U", "V") + "Z"

def new_uuid(): return str(uuid.uuid4())

# ---------------------------------------------------------------- layout
# entry: (col,row): ("hk", label, glyph, group, key, mods-dict, badge, new_binding_name or None)
#                   ("folder", label, page_name, glyph-group)
N = dict  # mods shortcut
NEW = "new"   # marks keys that still have to be bound in iRacing

PAGES = {
 "root": {
  (0,0): ("hk", "Zündung", "key", "car", "I", N(), None, None),
  (1,0): ("hk", "Starter", "power", "car", "S", N(), None, None),
  (2,0): ("hk", "Wischer", "wiper", "car", "W", N(ctrl=True, alt=True), None, None),
  (3,0): ("hk", "Tear-Off", "visor", "car", "T", N(alt=True), None, None),
  (4,0): ("hk", "Auto-FFB", "wheel", "ffb", "A", N(ctrl=True), "A", None),
  (0,1): ("hk", "FOV +", "fov", "view", "1", N(ctrl=True, shift=True), "+", None),
  (1,1): ("hk", "Sitz hoch", "seat", "view", "5", N(ctrl=True, shift=True), "up", None),
  (2,1): ("hk", "FFB +", "wheel", "ffb", "F2", N(ctrl=True, shift=True), "+", "IncFFB"),
  (3,1): ("folder", "Endurance", "endurance", "endu"),
  (4,1): ("folder", "Ansicht", "view", "view"),
  (0,2): ("hk", "FOV −", "fov", "view", "2", N(ctrl=True, shift=True), "-", None),
  (1,2): ("hk", "Sitz tief", "seat", "view", "6", N(ctrl=True, shift=True), "down", None),
  (2,2): ("hk", "FFB −", "wheel", "ffb", "F3", N(ctrl=True, shift=True), "-", "DecFFB"),
  (3,2): ("folder", "Audio", "audio", "audio"),
  (4,2): ("folder", "HUD & Tools", "hud", "hud"),
 },
 "view": {
  (1,0): ("hk", "Horizont ↑", "horizon", "view", "3", N(ctrl=True, shift=True), "up", None),
  (2,0): ("hk", "Kamera ▶", "cam", "view", "PGUP", N(), "right", None),
  (3,0): ("hk", "Spiegel", "mirror", "view", "M", N(alt=True), None, None),
  (4,0): ("hk", "FPS-Anzeige", "recenter", "view", "F", N(), None, None),
  (0,1): ("hk", "Standings", "pit", "view", "F2", N(), None, None),
  (1,1): ("hk", "Horizont ↓", "horizon", "view", "4", N(ctrl=True, shift=True), "down", None),
  (2,1): ("hk", "Kamera ◀", "cam", "view", "PGDN", N(), "left", None),
  (3,1): ("hk", "UI aus/an", "eyeoff", "view", "SPACE", N(), None, None),
  (4,1): ("hk", "Relative", "pit", "view", "F3", N(), None, None),
  (3,2): ("hk", "UI grösser", "zoom", "view", "PGUP", N(ctrl=True), "+", None),
  (4,2): ("hk", "UI kleiner", "zoom", "view", "PGDN", N(ctrl=True), "-", None),
 },
 "audio": {
  (1,0): ("hk", "Master +", "speaker", "audio", "F4", N(ctrl=True, shift=True), "+", "MasterVolumeUp"),
  (2,0): ("hk", "Spotter +", "headset", "audio", "F6", N(ctrl=True, shift=True), "+", "SPCCVolumeUp"),
  (3,0): ("hk", "Voice +", "mic", "audio", "F8", N(ctrl=True, shift=True), "+", "VChatVolumeUp"),
  (4,0): ("hk", "LFE +", "sub", "audio", "F1", N(ctrl=True, alt=True), "+", "LFEVolumeUp"),
  (1,1): ("hk", "Master −", "speaker", "audio", "F5", N(ctrl=True, shift=True), "-", "MasterVolumeDown"),
  (2,1): ("hk", "Spotter −", "headset", "audio", "F7", N(ctrl=True, shift=True), "-", "SPCCVolumeDown"),
  (3,1): ("hk", "Voice −", "mic", "audio", "F9", N(ctrl=True, shift=True), "-", "VChatVolumeDown"),
  (4,1): ("hk", "LFE −", "sub", "audio", "F2", N(ctrl=True, alt=True), "-", "LFEVolumeDown"),
  (2,2): ("hk", "Spotter still", "headset", "audio", "F10", N(ctrl=True, shift=True), "x", "SPCCShutUp"),
  (3,2): ("hk", "Voice Mute", "mic", "audio", "F3", N(ctrl=True, alt=True), "x", "VChatMute"),
 },
 "endurance": {
  (1,0): ("hk", "Fuel-Box", "fuel", "endu", "F4", N(), None, None),
  (2,0): ("hk", "Reifen-Box", "tire", "endu", "F5", N(), None, None),
  (3,0): ("hk", "Pit-Box", "pit", "endu", "F7", N(), None, None),
  (4,0): ("hk", "Alles ab", "clear", "endu", "7", N(), None, None),
  (0,1): ("hk", "Volle Box", "tire", "endu", "1", N(alt=True), "+", None),
  (1,1): ("hk", "Keine Reifen", "tire", "endu", "2", N(alt=True), "x", None),
  (2,1): ("hk", "Fast Repair", "wrench", "endu", "3", N(alt=True), None, None),
  (3,1): ("hk", "Sprit +5 l", "fuel", "endu", "4", N(alt=True), "+", None),
  (4,1): ("hk", "Sprit −5 l", "fuel", "endu", "5", N(alt=True), "-", None),
  (0,2): ("hk", "Pass Left", "chat", "car", "3", N(), "left", None),
  (1,2): ("hk", "Pass Right", "chat", "car", "4", N(), "right", None),
  (2,2): ("hk", "Sorry!", "chat", "car", "5", N(), None, None),
  (3,2): ("hk", "Thanks!", "chat", "car", "6", N(), None, None),
  (4,2): ("hk", "Fuel bis Ende", "flag", "endu", "F6", N(ctrl=True, alt=True), None, None),
 },
 "hud": {
  (1,0): ("hk", "Ideallinie", "line", "hud", "L", N(ctrl=True, alt=True), None, None),
  (2,0): ("hk", "Radar", "radar", "hud", "R", N(shift=True, alt=True), None, None),
  (3,0): ("hk", "Pit-Info", "pit", "hud", "F7", N(ctrl=True, alt=True), None, "PitSummaryToggle"),
  (4,0): ("hk", "Marker", "marker", "hud", "M", N(), None, None),
  (1,1): ("hk", "Reifen-Info", "tire", "hud", "F6", N(), None, None),
  (2,1): ("hk", "Fuel bis Ende", "flag", "hud", "F6", N(ctrl=True, alt=True), None, "FuelToEndToggle"),
  (3,1): ("hk", "Pedal-Anzeige", "line", "hud", "P", N(), None, None),
  (1,2): ("hk", "Screenshot", "shot", "hud", "S", N(ctrl=True, shift=True, alt=True), None, None),
  (3,2): ("hk", "Lackierung", "paint", "hud", "R", N(ctrl=True), None, None),
 },
}

# ---------------------------------------------------------------- build
STATE = {"FontFamily": "", "FontSize": 12, "FontStyle": "", "FontUnderline": False,
         "OutlineThickness": 2, "ShowTitle": False, "TitleAlignment": "bottom", "TitleColor": "#ffffff"}
PLUG = {"hotkey": {"Name": "Activate a Key Command", "UUID": "com.elgato.streamdeck.system.hotkey", "Version": "1.0"},
        "openchild": {"Name": "Create Folder", "UUID": "com.elgato.streamdeck.profile.openchild", "Version": "1.0"},
        "back": {"Name": "Open Parent Folder", "UUID": "com.elgato.streamdeck.profile.backtoparent", "Version": "1.0"}}

def action(kind, name, settings, image):
    st = dict(STATE); st["Image"] = image
    return {"ActionID": new_uuid(), "LinkedTitle": True, "Name": name, "Plugin": PLUG[kind],
            "Resources": None, "Settings": settings, "State": 0, "States": [st], "UUID": PLUG[kind]["UUID"]}

def build(out_path, profile_uuid=None, root_page=None, default_page=None, page_ids=None):
    """Pass the IDs of an existing profile to update it in place (ProfilesV3)."""
    profile_uuid = (profile_uuid or new_uuid()).upper()
    page_uuid = {p: new_uuid() for p in PAGES}
    if root_page: page_uuid["root"] = root_page.lower()
    for k, v in (page_ids or {}).items(): page_uuid[k] = v.lower()
    default_uuid = (default_page or new_uuid()).lower()
    root = f"{profile_uuid}.sdProfile"
    files, bindings = {}, []

    def add_image(page, png):
        name = encoded_id(new_uuid()) + ".png"
        files[f"{root}/Profiles/{page_uuid[page].upper()}/Images/{name}"] = png
        return f"Images/{name}"

    for page, keys in PAGES.items():
        acts = {}
        if page != "root":
            acts["0,0"] = action("back", "Parent Folder", {}, add_image(page, icon_png("back", C["nav"], "Zurück", "")))
        for (c, r), e in keys.items():
            if e[0] == "folder":
                _, label, target, grp = e
                img = add_image(page, icon_png("folder", C[grp], label, "Ordner"))
                acts[f"{c},{r}"] = action("openchild", "Create Folder", {"ProfileUUID": page_uuid[target]}, img)
            else:
                _, label, glyph, grp, key, mods, badge, newb = e
                hint = combo_text(key, **mods)
                img = add_image(page, icon_png(glyph, C[grp], label, hint, badge))
                acts[f"{c},{r}"] = action("hotkey", "Hotkey", hotkey(key, **mods), img)
                if newb: bindings.append((newb, label, hint))
        files[f"{root}/Profiles/{page_uuid[page].upper()}/manifest.json"] = json.dumps(
            {"Controllers": [{"Actions": acts, "Type": "Keypad"}], "Icon": "", "Name": ""}).encode()

    files[f"{root}/Profiles/{default_uuid.upper()}/manifest.json"] = json.dumps(
        {"Controllers": [{"Actions": None, "Type": "Keypad"}], "Icon": "", "Name": ""}).encode()
    files[f"{root}/manifest.json"] = json.dumps({
        "AppIdentifier": APP, **({"Device": {"Model": MODEL, "UUID": DEVICE_UUID}} if DEVICE_UUID else {}), "Name": "iRacing",
        "Pages": {"Current": page_uuid["root"], "Default": default_uuid, "Pages": [page_uuid["root"]]},
        "Version": "3.0"}).encode()

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p, data in files.items(): z.writestr(p, data)
    return bindings

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "iRacing.streamDeckProfile"
    ids = sys.argv[2:5]   # optional: <profile-uuid> <root-page-uuid> <default-page-uuid>
    for b in build(out, *ids): print("BIND", *b, sep=" | ")
    print("wrote", out)
