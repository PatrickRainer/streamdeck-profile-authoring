# Stream Deck Profile Authoring — an Agent Skill

An [Agent Skill](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) that teaches Claude (or any agent that reads `SKILL.md` skills) to **generate and edit Elgato Stream Deck profiles programmatically** — custom 144×144 key icons, hotkeys, folders and multi-page layouts — and to build them from a game's *real* keybindings instead of wiki guesses.

The Stream Deck profile format is undocumented, and most write-ups online are stale. The classic failure: the profile imports, every action lands in the right slot, but the keys show the generic glyph instead of your artwork. This skill writes down what actually works.

## What's inside

```
streamdeck-profile-authoring/
  SKILL.md                    the skill: format (V2 + V3), icon paths, ID encoding,
                              key codes, in-place updates, game-specific notes
  scripts/verify_profile.py   sanity-check a .streamDeckProfile before importing
  scripts/iracing_controls.py dump the bindings in an iRacing controls.cfg
examples/iracing/
  build_iracing_profile.py    complete generator: 64 keys, 6 pages (cockpit, view,
                              audio, HUD, endurance pit macros) for a 15-key deck
```

## Highlights

- **V2 (Stream Deck 6.x) and V3 (7.x, `ProfilesV3`) layouts** side by side.
- The **icon path rule** and the **27-char ID encoder**, with the encoder checked against Elgato's own default profile.
- Complete hotkey JSON incl. modifiers and the Win VK / scan code / Qt key-code triplet (the Qt codes are the ones people usually get wrong).
- Keyboard-layout pitfalls (e.g. Swiss-German `ü`/`¨` for US `[`/`]`).
- **Updating an installed profile in place**, no re-import needed.
- Game notes: **ETS2/ATS** (`controls.sii`) and **iRacing** (binary `controls.cfg` layout, modifier masks, active-profile lookup, pit-stop chat macros).

## Install

**Claude Code** – copy the skill folder into your skills directory:

```bash
git clone https://github.com/PatrickRainer/streamdeck-profile-authoring
cp -r streamdeck-profile-authoring/streamdeck-profile-authoring ~/.claude/skills/
```

**Claude apps** – zip the `streamdeck-profile-authoring/` folder and upload it under *Settings → Capabilities → Skills*.

Then just ask, e.g. *"Make me a Stream Deck profile for iRacing with the functions that aren't on my wheel."*

## Example generator

```bash
pip install cairosvg pillow
python3 examples/iracing/build_iracing_profile.py iRacing.streamDeckProfile
python3 streamdeck-profile-authoring/scripts/verify_profile.py iRacing.streamDeckProfile
```

Edit the `PAGES` table to move keys around. Before you build, check the key choices in the script: FOV, horizon and seat height use Ctrl+Shift+1…6 (bind those in iRacing too), and the Ctrl+Shift / Ctrl+Alt F-key combos for actions iRacing leaves unbound have to be assigned in iRacing too.

## Status & caveats

Not affiliated with Elgato or iRacing. Tested on Windows with Stream Deck 6.x and 7.5 and a 15-key MK.2. The iRacing `controls.cfg` layout is reverse-engineered, so back up the file before patching it. Corrections via issues or PRs are welcome, especially from other app versions, decks and keyboard layouts.

## License

MIT
