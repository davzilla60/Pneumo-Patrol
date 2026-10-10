"""Build index.html / patrol.embed.html from patrol.html + assets/.

For every case in CASES:
  assets/<id>_xray.jpg      the plain chest radiograph
  assets/<id>_mask_src.*    white-on-black pneumothorax mask, same size as the x-ray
                            (omit for a "ptx": False case)
The build makes, per case:
  - a tinted overlay PNG (red fill + gold outline) used for the answer reveal
  - a 128x128 hit-grid (mask dilated by HIT_TOLERANCE) used to score the player's markers
  - a small thumbnail for the debrief screen
then base64-inlines everything so the output is one self-contained file.

Usage:  python build.py
"""
import base64, io, json
from pathlib import Path
from PIL import Image, ImageFilter, ImageChops

ROOT = Path(__file__).parent
A = ROOT / "assets"

GRID = 128              # hit-grid resolution
HIT_TOLERANCE = 0.04    # marker counts as "on target" within 4% of image width of the mask

# Waves, in play order. The first wave is the opening wave: classify all of its
# cases correctly to unlock "No Lung Left Behind".
# Add waves here as more cases arrive (e.g. "Edge Runners", "Stealth Fleet" for subtler / supine cases).
WAVES = [
    {"name": "Opening Salvo", "blurb": "Three incoming cases. Classify every one correctly to unlock the badge."},
    {"name": "Friend or Foe", "blurb": "Not every contact is hostile. Clear films are friendly: hold your fire."},
    {"name": "Stealth Fleet", "blurb": "Smaller apical collections. Look behind the clavicles and first ribs, on both sides."},
]

# "wave" is the index into WAVES. "ptx": False marks a normal (no pneumothorax) case.
# "source" is a key into SOURCES (defaults to "ptx498").
# Text is shown on the answer reveal.
CASES = [
    {
        "id": "case01", "wave": 0, "ptx": True,
        "title": "Right apicolateral pneumothorax",
        "summary": "Right pneumothorax over the apex, tracking down the lateral upper zone.",
        "findings": [
            "Thin white visceral pleural line curving under the right apex and down the lateral wall.",
            "Lateral to the line the lung is black, with no vessels crossing it.",
            "Trachea and mediastinum central: simple, not tension.",
        ],
    },
    {
        "id": "case03", "wave": 0, "ptx": True,
        "title": "Large right pneumothorax",
        "summary": "Large right pneumothorax from the apex to the costophrenic angle, with the right lung collapsed towards the hilum.",
        "findings": [
            "The edge of the collapsed right lung is visible as a curved white line in the mid zone.",
            "Everything between that edge and the chest wall is black, with no lung markings, from apex to base.",
            "Compare the two sides: the right hemithorax is darker than the left because it is mostly air.",
        ],
    },
    {
        "id": "case05", "wave": 0, "ptx": True,
        "title": "Large left pneumothorax",
        "summary": "Large left pneumothorax from the apex down the whole lateral chest wall, with the left lung collapsed medially.",
        "findings": [
            "The collapsed left lung sits next to the heart border, outlined by its visceral pleural edge.",
            "A wide black band with no vessels runs from the left apex to the costophrenic angle.",
            "The marker &ldquo;右&rdquo; means &ldquo;right&rdquo;, so the pneumothorax is on the patient&rsquo;s left.",
        ],
    },
    # ---- wave 2: friend or foe -------------------------------------------------------
    {
        "id": "norm01", "wave": 1, "ptx": False, "source": "cradi",
        "title": "No pneumothorax: lines and clips",
        "summary": "No pneumothorax. A line enters from the right neck and metallic surgical clips project over the right upper zone.",
        "findings": [
            "Lung markings continue all the way out to the chest wall on both sides.",
            "Tubes, lines and clips create edges that can mimic a pleural line: follow each one and check that markings continue beyond it.",
            "Both apices contain vessels, with no black, empty rim.",
        ],
    },
    {
        "id": "case02", "wave": 1, "ptx": True,
        "title": "Small right apical pneumothorax",
        "summary": "Small right pneumothorax confined to the apex.",
        "findings": [
            "Thin curved pleural line arching under the right apex, just below the clavicle.",
            "Above the line the apex is slightly blacker, with no vessels crossing it.",
            "Small apical collections hide behind the clavicle and first rib: check both apices on every film.",
        ],
    },
    {
        "id": "norm02", "wave": 1, "ptx": False, "source": "cradi",
        "title": "No pneumothorax: busy film",
        "summary": "No pneumothorax. Overlapping scapulae, soft tissues and stomach gas make this a busy film, but both lungs reach the chest wall.",
        "findings": [
            "Lung markings reach the periphery of both lungs, including the apices.",
            "Scapular edges and soft-tissue folds can look like a pleural line; a true pleural edge has no lung markings beyond it.",
            "The air&ndash;fluid level below the left hemidiaphragm is gas in the stomach, not air in the pleural space.",
        ],
    },
    {
        "id": "case04", "wave": 1, "ptx": True,
        "title": "Small left apical pneumothorax",
        "summary": "Small left pneumothorax over the apex, curving down a short way laterally.",
        "findings": [
            "Fine pleural edge arching over the left apex beneath the clavicle and first rib.",
            "Lateral and above the line there are no lung markings.",
            "The marker here is &ldquo;L&rdquo;, on the patient&rsquo;s left: always check the side marker.",
        ],
    },
    # ---- wave 3: stealth fleet -------------------------------------------------------
    {
        "id": "case06", "wave": 2, "ptx": True,
        "title": "Right apicolateral pneumothorax",
        "summary": "Right pneumothorax over the apex, tracking down the lateral upper zone.",
        "findings": [
            "Visceral pleural line curving under the right apex and running down the lateral wall.",
            "The space outside the line is black and empty of vessels.",
            "Overlapping ribs and clavicle can hide the edge: trace it rib by rib.",
        ],
    },
    {
        "id": "norm03", "wave": 2, "ptx": False, "source": "cradi",
        "title": "Normal chest: no pneumothorax",
        "summary": "Normal chest radiograph. Both lungs are fully expanded.",
        "findings": [
            "The apices look dark, but vessels can be traced into them: that is aerated lung, not a pneumothorax.",
            "Both lungs reach the chest wall, with sharp costophrenic angles.",
            "Dark is not the same as empty. Look for the absence of markings beyond a thin white line.",
        ],
    },
    {
        "id": "case07", "wave": 2, "ptx": True,
        "title": "Left apicolateral pneumothorax",
        "summary": "Thin left pneumothorax over the apex, extending down the lateral upper zone.",
        "findings": [
            "Very thin pleural line following the curve of the left apex and upper chest wall.",
            "Only a narrow rim of air: easy to mistake for a rib edge or skin fold.",
            "A skin fold usually runs beyond the chest wall; a pleural edge stays inside it and has no markings outside it.",
        ],
    },
]

# Image source attribution (CC BY 4.0: creator, title, source link, licence link, changes).
SOURCES = {
    "ptx498": {
        "citation": "Wang, Y. (2021). PTX-498: A multi-center pneumothorax segmentation chest X-ray "
                    "image dataset [Data set]. In Neurocomputing (Version v2-fix, Vol. 454, pp. 201–211). Zenodo.",
        "url": "https://doi.org/10.5281/zenodo.8266529",
        "used": "pneumothorax cases",
        "changes": "segmentation masks rendered as coloured answer overlays and scoring regions; "
                   "one mask recovered from a pre-overlaid preview image",
    },
    "cradi": {
        "citation": "Liu, M., & Xie, X. (2021). Chest Radiograph at Diverse Institutes (CRADI) dataset [Data set]. Zenodo.",
        "url": "https://doi.org/10.5281/zenodo.5493595",
        "used": "no-pneumothorax cases",
        "changes": "converted to greyscale JPEG and resized to 1024 px",
    },
}

FILL = (255, 70, 90)      # overlay tint
EDGE = (255, 230, 120)    # outline of the pneumothorax / pleural edge


def find_mask(cid):
    for ext in (".png", ".jpg", ".jpeg"):
        p = A / f"{cid}_mask_src{ext}"
        if p.exists():
            return p
    raise FileNotFoundError(f"no mask for {cid}")


def load_mask(cid):
    m = Image.open(find_mask(cid)).convert("L")
    return m.point(lambda v: 255 if v > 127 else 0).filter(ImageFilter.MedianFilter(5))


def make_overlay(cid, m):
    edge = ImageChops.subtract(m.filter(ImageFilter.MaxFilter(7)), m.filter(ImageFilter.MinFilter(3)))
    out = Image.new("RGBA", m.size, FILL + (0,))
    out.putalpha(m.point(lambda v: int(v * 0.42)))
    edge_layer = Image.new("RGBA", m.size, EDGE + (0,))
    edge_layer.putalpha(edge)
    out = Image.alpha_composite(out, edge_layer)
    p = A / f"{cid}_overlay.png"
    out.save(p, optimize=True)
    return p


def make_hitgrid(m):
    """Mask dilated by HIT_TOLERANCE, packed as GRID*GRID bits (row-major, MSB first)."""
    small = m.resize((256, 256), Image.BILINEAR).point(lambda v: 255 if v > 40 else 0)
    r = max(1, round(HIT_TOLERANCE * 256))
    small = small.filter(ImageFilter.MaxFilter(2 * r + 1))
    g = small.resize((GRID, GRID), Image.BOX).point(lambda v: 255 if v > 0 else 0)
    px = g.load()
    bits = bytearray(GRID * GRID // 8)
    for y in range(GRID):
        for x in range(GRID):
            if px[x, y]:
                i = y * GRID + x
                bits[i >> 3] |= 0x80 >> (i & 7)
    return base64.b64encode(bytes(bits)).decode()


def make_thumb(p):
    im = Image.open(p).convert("L")
    im.thumbnail((160, 160))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=70)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def data_uri(p):
    mime = "image/png" if p.suffix == ".png" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def main():
    cases = []
    for c in CASES:
        xray = A / f"{c['id']}_xray.jpg"
        entry = {"source": "ptx498", **c, "xray": data_uri(xray), "thumb": make_thumb(xray), "overlay": None, "hit": None}
        if c["ptx"]:
            m = load_mask(c["id"])
            entry["overlay"] = data_uri(make_overlay(c["id"], m))
            entry["hit"] = make_hitgrid(m)
        cases.append(entry)
    assets = {k: data_uri(A / f"{k}.png") for k in ("logo_full", "logo_mark")}
    src = (ROOT / "patrol.html").read_text(encoding="utf-8")
    out = (src.replace("/*__CASES__*/[]", json.dumps(cases))
              .replace("/*__WAVES__*/[]", json.dumps(WAVES))
              .replace("/*__SOURCE__*/{}", json.dumps(SOURCES))
              .replace("/*__ASSETS__*/{}", json.dumps(assets))
              .replace("/*__GRID__*/0", str(GRID)))
    (ROOT / "patrol.embed.html").write_text(out, encoding="utf-8")
    (ROOT / "index.html").write_text(out, encoding="utf-8")
    print(f"built {len(cases)} case(s) in {len(WAVES)} wave(s), {len(out)/1e6:.2f} MB")


if __name__ == "__main__":
    main()
