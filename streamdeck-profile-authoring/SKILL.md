---
name: streamdeck-profile-authoring
description: >
  Build or edit Elgato Stream Deck `.streamDeckProfile` bundles programmatically —
  custom key icons, hotkey actions, folders, multi-page layouts. Use this skill
  whenever a `.streamDeckProfile` is being generated, unpacked, or repaired; when
  someone asks for a Stream Deck profile for a game or application; when an
  installed profile under `ProfilesV3` should be edited in place; or when custom
  key icons import successfully as actions but render as the default action glyph
  instead of the artwork. Also use it when hand-writing Stream Deck `manifest.json`
  files, deriving Stream Deck page/folder IDs, or mapping a game's keyboard
  bindings (ETS2/ATS `controls.sii`, iRacing `controls.cfg`) onto a Stream Deck
  grid — even if the user never says "manifest" or "profile format".
license: MIT
metadata:
  version: "1.2"
---

# Authoring Stream Deck profile bundles by hand

How to generate a `.streamDeckProfile` that imports cleanly **with its custom icons
intact**, and how to update an already-installed profile without re-importing. The
actions are the easy part; the icon referencing is what silently fails.

**Failure pattern:** the profile imports, every key lands in the right slot with the
right action, but the keys show the generic action glyph instead of the custom
artwork — or exactly one key on each page shows its icon and the rest don't.

**Evidence behind this skill**
- A 5-page / 59-key V2 bundle imported into Stream Deck 6.x on Windows with all 59
  custom icons rendering.
- The ID encoder below reproduces all 7 folder IDs in Elgato's own shipped
  `StreamDeck_winDefault.streamDeckProfile`.
- On Stream Deck 7.5.1 (Windows), a V3 bundle built as described below was imported
  and landed in `ProfilesV3` with pages, folders and images intact, and a V2 bundle
  imported earlier had been migrated to the V3 layout by the app.

## Rule zero: read real profiles before guessing

The format is undocumented and the community write-ups online are **wrong or stale**.
Do not guess and do not trust search results. Ground truth, in order of preference:

1. **The user's own installed profiles** — the app keeps them unzipped:
   - Windows: `%APPDATA%\Elgato\StreamDeck\ProfilesV3\<UUID>.sdProfile\`
   - macOS: `~/Library/Application Support/com.elgato.StreamDeck/ProfilesV3/`
   (`ProfilesV2` on 6.x.) These show the exact format of the user's app version,
   the device `Model` string, and any real recorded hotkeys.
2. **Elgato's shipped defaults** in the install directory:
   `<install dir>/DefaultProfiles/*.streamDeckProfile` (Windows default
   `C:\Program Files\Elgato\StreamDeck\DefaultProfiles\`, but it may be installed
   elsewhere — the app log `logs/StreamDeck.log` prints `PATH` and `VERSION` at the
   top of every session). `StreamDeck_winDefault.streamDeckProfile` has folders,
   custom icons and multiple page types.
3. If neither is reachable: have the user set one custom icon by hand, export the
   profile, and read that.

## Format versions

| | V2 (Stream Deck 6.x) | V3 (Stream Deck 7.x, `ProfilesV3`) |
|---|---|---|
| Top-level `Version` | `"2.0"` | `"3.0"` |
| Page/folder directory name | encoded 27-char id (see below) | the page UUID, **uppercase, plain** |
| Image filenames | encoded 27-char id `.png` | encoded 27-char id `.png` (unchanged) |
| UUIDs inside JSON | lowercase | lowercase |
| Action objects | no `Plugin` block | `Plugin {Name, UUID, Version}` + `"Resources": null` |
| `Pages.Default` | usually same as `Current` | a separate, empty page with its own directory |

Stream Deck 7.x imports V2 bundles and migrates them. When you know the user's app is
7.x, emit V3 — it's exactly what the app writes to disk, so there's nothing left to
migrate. Mirror whatever their `ProfilesV3` shows if it differs from this table.

## Package structure

A `.streamDeckProfile` is a plain ZIP:

```
<PROFILE-UUID>.sdProfile/
  manifest.json                       top level
  Profiles/<PAGE-DIR>/                one directory per page AND per folder
    manifest.json                     that page's keys
    Images/<ENCODED-ID>.png           144x144 key icons
```

`<PAGE-DIR>` is the uppercase page UUID in V3, or `profile_folder_id(uuid)` in V2.

Top-level `manifest.json` (V3):

```json
{
  "AppIdentifier": "C:\\Path\\To\\Game.exe",
  "Device": {"Model": "20GBA9901", "UUID": "<device id>"},
  "Name": "My Profile",
  "Pages": {"Current": "<root-uuid>", "Default": "<default-uuid>", "Pages": ["<root-uuid>"]},
  "Version": "3.0"
}
```

- `Pages.Pages` lists only the **deck pages** (the `1 +` pager in the app). Folder
  pages get their own directory but are NOT listed — they're reached via their
  parent's folder action.
- `AppIdentifier` (optional) is the executable that auto-switches to this profile.
  Copy it from the user's existing profile for that game if there is one.
- `Device` is optional. Copy it from one of the user's installed profiles if you
  want it; otherwise omit it and the profile imports onto any matching deck. The
  `UUID` is a device serial — don't publish real ones in shared examples.
  Grid sizes: MK.2 / original (15 keys, model `20GBA9901` for MK.2) = 5x3,
  XL = 8x4, Mini = 3x2.

Page `manifest.json`:

```json
{
  "Controllers": [ { "Actions": { "0,0": {...}, "1,0": {...} }, "Type": "Keypad" } ],
  "Icon": "",
  "Name": ""
}
```

Keys are addressed `"<col>,<row>"`, zero-based, `0,0` top-left. An empty page has
`"Actions": null`.

## The two things that actually break

### 1. Icon path

`States[0].Image` must be **`"Images/<id>.png"`, relative to that page's directory**.
Anything else fails silently — the key renders the default action glyph.

### 2. ID encoding

Image filenames (both versions) and V2 page directory names use this encoding of a
UUID (for images, encode a throwaway UUID):

```python
def profile_folder_id(u: str) -> str:
    """UUID -> Stream Deck's 27-char directory/image id."""
    raw = u.replace("-", "") + "000"          # pad to a multiple of 5 hex digits
    out = ""
    for i in range(0, len(raw), 5):           # 5 hex digits at a time
        n = int(raw[i:i + 5], 16)
        s = ""
        while n:
            s = "0123456789abcdefghijklmnopqrstuv"[n % 32] + s
            n //= 32
        out += s.rjust(4, "0")                # base32, zero-padded to 4
    return out[:26].upper().replace("V", "W").replace("U", "V") + "Z"
```

The `V→W` then `U→V` substitution order matters, and every id ends in `Z`.

**Validate your implementation** before generating a V2 bundle: encode the
`Pages.Current`, `Pages.Default`, every `Pages.Pages` entry, and every folder
action's `Settings.ProfileUUID` from Elgato's V2 default profile, and confirm each
result is an existing directory under `Profiles/`. All of them must hit.

## Action objects

Every key is one action object (V3 shape; drop `Plugin` and `Resources` for V2):

```json
{
  "ActionID": "<lowercase uuid4, unique per key>",
  "LinkedTitle": true,
  "Name": "Hotkey",
  "Plugin": {"Name": "Activate a Key Command", "UUID": "com.elgato.streamdeck.system.hotkey", "Version": "1.0"},
  "Resources": null,
  "Settings": { },
  "State": 0,
  "States": [ {
    "FontFamily": "", "FontSize": 12, "FontStyle": "", "FontUnderline": false,
    "Image": "Images/<ENCODED-ID>.png",
    "OutlineThickness": 2,
    "ShowTitle": false, "Title": "",
    "TitleAlignment": "bottom", "TitleColor": "#ffffff"
  } ],
  "UUID": "com.elgato.streamdeck.system.hotkey"
}
```

| Purpose | `UUID` | `Name` / `Plugin.Name` | `Settings` |
|---|---|---|---|
| Send a keystroke | `com.elgato.streamdeck.system.hotkey` | `Hotkey` / `Activate a Key Command` | see below |
| Open a sub-folder | `com.elgato.streamdeck.profile.openchild` | `Create Folder` / `Create Folder` | `{"ProfileUUID": "<child page uuid>"}` |
| Back out of a folder | `com.elgato.streamdeck.profile.backtoparent` | `Parent Folder` / `Open Parent Folder` | `{}` |
| Open a file/app | `com.elgato.streamdeck.system.open` | `Open` | `{"openInBrowser": true, "path": "..."}` |
| Open a URL | `com.elgato.streamdeck.system.website` | `Website` | `{"openInBrowser": true, "path": "..."}` |

Hotkey `Settings` — note the trailing sentinel entry, which Stream Deck always writes:

```json
{"Hotkeys": [
  {"KeyCmd": false, "KeyCtrl": true, "KeyModifiers": 2, "KeyOption": false,
   "KeyShift": false, "NativeCode": 18, "QTKeyCode": 69, "VKeyCode": 69},
  {"KeyCmd": false, "KeyCtrl": false, "KeyModifiers": 0, "KeyOption": false,
   "KeyShift": false, "NativeCode": 146, "QTKeyCode": 33554431, "VKeyCode": -1}
]}
```

### Modifiers

Set the booleans **and** the `KeyModifiers` bitmask on the key entry itself:
Shift = 1, Ctrl = 2, Alt (`KeyOption`) = 4. Ctrl = 2 is confirmed from a profile
recorded in the app; Shift = 1 and Alt = 4 follow the same scheme but haven't been
checked against an app-recorded profile — if you can, compare with one the user
recorded.

Avoid combos the OS or other tools grab: anything with `Alt+F4` (even with Ctrl
added), `Ctrl+Shift+Esc`, `Ctrl+Shift+0` (input-language switch on some systems),
and GPU overlay hotkeys (NVIDIA uses many `Alt+…`).

### Key codes

Three per key, all required: `VKeyCode` = Windows virtual-key, `NativeCode` = set-1
scan code, `QTKeyCode` = Qt key code. (Profiles recorded in the app have been seen
with `NativeCode` equal to the VK for arrow keys; scan codes have worked fine in
generated profiles.)

- **Letters `A`–`Z`**: VKey and QT are both `ord(upper)`. Scan codes:
  `A30 B48 C46 D32 E18 F33 G34 H35 I23 J36 K37 L38 M50 N49 O24 P25 Q16 R19 S31 T20
  U22 V47 W17 X45 Y21 Z44`
- **Digits `1`–`9`,`0`**: VKey and QT are `ord(char)`; scan codes are `2`–`11` in order.

| Key | VKey | Scan | Qt |
|---|---|---|---|
| `[` (US) | 219 (`VK_OEM_4`) | 26 | 91 |
| `]` (US) | 221 (`VK_OEM_6`) | 27 | 93 |
| `;` (US) | 186 (`VK_OEM_1`) | 39 | 59 |
| `'` (US) | 222 (`VK_OEM_7`) | 40 | 39 |
| Space | 32 | 57 | 32 |
| Enter | 13 | 28 | 16777220 |
| Esc | 27 | 1 | 16777216 |
| PageUp | 33 | 73 | 16777238 |
| PageDown | 34 | 81 | 16777239 |
| Arrows ←↑→↓ | 37–40 | 75/72/77/80 | 16777234–16777237 |
| F*n* | 111+*n* | F1=59…F10=68, F11=87, F12=88 | 16777263+*n* |

Qt uses `0x01000000`-based codes for non-printing keys — those are the ones most
often guessed wrong. `Qt::Key_F1 = 0x01000030`, so F10 = `0x01000039` = 16777273.

**Punctuation keys depend on the keyboard layout.** `VK_OEM_*` values are assigned
per layout to physical positions, so the "same" VK is a different key on QWERTZ or
AZERTY. Games that read DirectInput go by physical position. Example — the
physical keys right of `P` are US `[` `]`, but on Swiss-German they are `ü`
(`VK_OEM_1` = 186, Qt `Key_Udiaeresis` = 220, scan 26) and `¨` (`VK_OEM_3` = 192,
Qt `Key_Diaeresis` = 168, scan 27). Ask about or infer the layout, label the key
icon with the character the user actually sees, and tell them that re-recording
the key in the Stream Deck app fixes it if it doesn't fire.

## Procedure — new bundle to import

- [ ] 1. Read one of the user's installed profiles (or Elgato's default) and confirm
      the field names and version against this skill; prefer the file.
- [ ] 2. For V2, implement `profile_folder_id` and validate it against every UUID in
      a reference V2 profile. Do not proceed until all match.
- [ ] 3. Build the page tree: one UUID per page/folder, root listed in
      `Pages.Pages`, folders reached only via `openchild` actions. V3: add the
      separate empty `Default` page.
- [ ] 4. Render icons at **144x144 PNG**. `cairosvg` (`pip install cairosvg`) is the
      reliable SVG rasterizer; ImageMagick's built-in SVG renderer mangles paths.
      Put the key combo as a small second line on the icon — it doubles as
      documentation when the user binds things in-game.
- [ ] 5. Write each icon to `Profiles/<page-dir>/Images/<fresh-encoded-id>.png` and
      point that key's `States[0].Image` at `Images/<same-id>.png`.
- [ ] 6. Zip with forward slashes, no extra top-level wrapper directory — the
      `<UUID>.sdProfile/` directory must be at the archive root.
- [ ] 7. Run the verification pass below (`scripts/verify_profile.py`).
- [ ] 8. Tell the user to **delete any previously imported copy first**, then
      double-click the file. Re-importing without deleting leaves two same-named
      profiles and it's ambiguous which one they're looking at.

## Procedure — update an installed profile in place (no re-import)

Useful when the user already imported a profile and wants a revision, or wants to
keep the profile's identity.

1. **The Stream Deck app must be fully quit** (tray → Quit), not just closed to the
   tray. A running app keeps profiles in memory and overwrites your edits. Confirm
   from the log rather than trusting "done": the last lines of
   `logs/StreamDeck.log` read `Application session ended`.
2. Find the profile by `Name` in `ProfilesV3/*/manifest.json` — it may not be the
   UUID you generated; import can assign a new one.
3. Copy the whole `.sdProfile` directory to a backup location first.
4. Rebuild with the **existing** profile UUID, root page UUID, `Default` page UUID,
   and reuse existing folder page UUIDs where folders persist (map them by which
   root key opens them). Reusing IDs avoids orphan directories, which matters
   because deleting files may need explicit permission.
5. Write the files over the existing directory (an unzip over the top is fine),
   then check every `Images/…` referenced from every page manifest exists.
6. The user starts the app again. Leftover unreferenced PNGs are harmless.

### Verification pass (do this every time; it catches everything cheaply)

`python3 scripts/verify_profile.py <file.streamDeckProfile>` asserts:

- every `States[0].Image` matches `Images/<26 chars>Z.png` and exists in the zip
- `ActionID`s are unique across the whole profile, and image filenames are unique
- every icon is 144x144
- every `openchild` `ProfileUUID` resolves to an existing page directory
- every non-root page with keys has exactly one `backtoparent`; the root has none
- all coordinates fall inside the target grid

## Building a profile for a specific game

Don't trust wikis for keybinds — **read the game's own config**, and skip actions
already on the user's wheel/HOTAS so the deck adds what's missing.

### Euro Truck Simulator 2 / American Truck Simulator

Live bindings are in `Documents/<Game>/steam_profiles/<hex-id>/controls.sii` (or
`profiles/<hex-id>/` for non-Steam). Grep the
`config_lines[N]: "mix <action> \`keyboard.<key>\`"` entries. Actions with
`` `unbound?0` `` have no keyboard binding and must be skipped.

Real corrections this caught that the wikis had wrong: `radionext` is `PgDn` and
`radioprev` is `PgUp` (wikis list them reversed); ETS2's cruise increment/decrement
ship unbound on keyboard; the hazards action is `flasher4way`, not a "warning" name.

### iRacing

- Bindings live in `Documents/iRacing/profiles/controls/<profile>/controls.cfg`
  (binary, magic `GFCC`). A top-level `Documents/iRacing/controls.cfg` may be a
  stale leftover. The **active** profile is in `app.ini` under `[ControlProfiles]`:
  `Global=<profile>` plus per-car overrides like `porsche9922cup=porsche9922cup`.
  Read (and edit) all of them, not just the one with the friendliest name.
- `scripts/iracing_controls.py` dumps every binding. Record layout as observed:
  the action name, NUL, then a fixed 68-byte block:
  `u32 ?, u32 flags (6/0x19/0x1f), u32 type, u32 key, u32 modmask, …zeros`.
  `type` 0 = unbound, 1 = axis, 2 = joystick button (device GUIDs follow),
  4 = keyboard.
- Keyboard codes: letters and digits = ASCII uppercase; PgUp/PgDn/Space/Ins/Del/
  arrows = Windows VK; F1…F12 = 197…208; the US `[` `]` keys are 118/120 and
  `-` `=` are 108/114. Modifier mask: Shift `0x30000`, Ctrl `0xC0000`,
  Alt `0x300000` (they combine: Ctrl+Shift `0xF0000`, Ctrl+Alt `0x3C0000`).
- Useful defaults to cross-check against: in-car FOV `]`/`[`, horizon
  `Shift+]`/`Shift+[`, seat height `Ctrl+]`/`Ctrl+[`, black boxes F1…F12,
  chat macros `1`…`0` and `Alt+1`…`Alt+5`.
- Many useful actions ship **unbound** (FFB strength `IncFFB`/`DecFFB`, master/
  spotter/voice/LFE volume, spotter shut-up, voice mute, pit summary, fuel-to-end).
  Either tell the user to bind them (click the action in Options → Controls, then
  press the Stream Deck key), or — with iRacing **closed** and a backup made —
  patch the unbound records in place: set `type=4`, `key`, `modmask`. Only touch
  records whose `type` is 0; never overwrite a wheel binding. File size must not
  change. This worked syntactically in testing; have the user confirm the binding
  shows up in Options → Controls.
- Pit-stop control is via chat macros `AutoChatStr1…15` in `app.ini` (a trailing
  `$` sends immediately): `#lf rf lr rr ws$` (4 tyres + tear-off), `#cleartires$`,
  `#fr$` (fast repair, toggles), `#fuel +5l$`, `#clear$`. Point Stream Deck keys at
  the macro's chat key rather than typing text. Preserve the file's CRLF endings
  and `; comment` columns when editing.
- Hotkeys are one-way: a key can't show whether fast repair or a toggle is on. For
  live state on keys, use a telemetry plugin (e.g. iRaceDeck from the Elgato
  marketplace) instead of a plain profile.

## Gotchas

- **Icons are the only hard part.** If actions land correctly but artwork doesn't,
  it is always the `Image` path — not the action type, not the ActionID, not the
  device model.
- **A screenshot showing exactly one working icon is ambiguous.** It can mean "one
  scheme is right" or "one file happened to be reachable". When diagnosing, make
  every test key differ in exactly one variable, and prefer reading a known-good
  profile over another import round-trip.
- **Bare modifiers can't be hotkeys.** Stream Deck won't reliably send a lone
  `Shift`/`Alt`/`Ctrl`. Skip those bindings and say so.
- **Hotkeys go to the focused window.** Games that ignore injected input often work
  once the Stream Deck app runs as administrator.
- **Hotkey actions are one-way** — they can't read application state, so a toggle
  key can't reflect on/off. That needs a telemetry plugin, not a profile.
- **Ship the generator.** Emit the build script alongside the profile so layout
  tweaks don't require regenerating from scratch, and guard it with
  `if __name__ == "__main__":` — importing it for verification otherwise re-runs the
  whole build. Let it accept existing profile/page UUIDs so the same script can do
  in-place updates.
- **Sandboxes may block deletes** on synced folders (OneDrive etc.). Build in a
  temp directory and copy the finished artifact out, rather than rebuilding in place.
- **The user may act between your turns.** Before an in-place update, re-list
  `ProfilesV3` — they may have deleted the old profile and imported your previous
  build under a new UUID.

## What didn't work

Each of these produced a clean import with **no** custom icons:

- `"Image": "data:image/png;base64,..."` inline in the manifest. Widely claimed to
  work; it does not, and it also overrides any on-disk file so it masks a correct
  path.
- `"Image": "state0.png"` with the file at `<col>,<row>/CustomImages/state0.png`.
  The `<col>,<row>/CustomImages/` layout appears in older community docs and is not
  what current Stream Deck reads.
- `"Image": ""` or omitting `Image` entirely, relying on the folder layout implicitly.
- `"Image": "img0.png"` with the file at `Images/img0.png` — right directory, but the
  value must include the `Images/` prefix.
- Blaming duplicate `ActionID`s (all keys sharing `00000000-...-0`). Making them
  unique is correct and worth doing, but it was **not** the cause; the icons stayed
  broken until the path was fixed.
