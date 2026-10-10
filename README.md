# Pneumo Patrol

A Rad-Lad chest X-ray arcade game inspired by classic space-invader games. An incoming spacecraft beams down a chest radiograph. The arcade pauses while the player inspects it, classifies it as **No pneumothorax** or **Pneumothorax**, and, if it is a pneumothorax, marks where it is. Submitting reveals the answer overlay and an explanation.

Pressing Start plays a short "Defend the Free Earth" intro crawl first. **Skip intro**, Esc, Space or Enter skips it.

- **Scoring:** correct classification +100, accurate localisation +50 bonus (every marker within 4% of image width of the true pneumothorax), streak bonus +10 per consecutive correct answer (max +50), speed bonus up to +50 in Patrol mode (decays over 60 s).
- **Modes:** Patrol (speed bonus, high score saved in the browser) and Practice (untimed).
- **Viewer:** wheel/pinch zoom, drag to pan, fit, invert, fullscreen. Up to 3 markers (mark both sides for bilateral cases).
- **Missed cases** are listed on the debrief and can be revisited (no points).
- **Achievement: No Lung Left Behind.** Unlocks when every case in the opening wave is classified correctly. Localisation bonuses don't count towards it. The badge and its toast stay hidden until the opening wave has at least 3 cases (`ACH_MIN` in `patrol.html`).
- Sound toggle (synthesised chip sounds, no audio files). Keys: `N`/`P` choose, `Enter` submit/next, `+`/`-`/`0` zoom, `F` fullscreen, `I` invert, `O` overlay, `S` sound.

## Files

| File | Purpose |
|---|---|
| `index.html` / `patrol.embed.html` | Built, self-contained game (all images inlined). Embed this. |
| `patrol.html` | Source page (placeholders get filled in by the build) |
| `build.py` | Case list, waves, and the build |
| `assets/` | `<id>_xray.jpg`, `<id>_mask_src.jpg` (white-on-black mask), generated `<id>_overlay.png`, Rad-Lad logos |

## Adding cases

1. Drop `assets/caseNN_xray.jpg` and `assets/caseNN_mask_src.jpg` (same size, white = pneumothorax).
2. Add an entry to `CASES` in `build.py` (`wave`, `ptx`, title, summary, findings). For a normal case, set `"ptx": False` and leave out the mask.
3. Add waves to `WAVES` as needed (the first wave is the opening wave for the achievement).
4. `python build.py` (needs Pillow).

## Image source

Wang, Y. (2021). PTX-498: A multi-center pneumothorax segmentation chest X-ray image dataset [Data set]. In Neurocomputing (Version v2-fix, Vol. 454, pp. 201–211). Zenodo. https://doi.org/10.5281/zenodo.8266529. Licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Changes: segmentation masks rendered as coloured answer overlays and scoring regions.

Teaching game, not for clinical use.
