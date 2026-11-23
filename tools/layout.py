"""Lay out all copies by material and export a pure-cut drawing and its registration map."""

import math
from pattern import DOWNLOAD, ASSETS, make, tidy, MATERIALS
import json


def xy(n):
    return f"{n:.3f}".rstrip("0").rstrip(".") or "0"


def path(points, close=False):
    return (
        "M" + " L".join(f"{xy(x)} {xy(y)}" for x, y in points) + (" Z" if close else "")
    )


def pack(data, material):
    limit = {"outer": 900, "thin": 275, "board": 175}[material]
    gap = 7
    border = 8
    boxes = []
    for key, p in data["parts"].items():
        if p["material"] != material:
            continue
        x, y, X, Y = p["bbox"]
        for i in range(p["qty"]):
            flip = key in "BC" and i >= p["qty"] // 2
            boxes.append(dict(key=key, copy=i + 1, flip=flip, w=X - x, h=Y - y))
    boxes.sort(key=lambda b: -b["h"])
    placed = []
    for box in boxes:
        options = {border} | {p["x"] + p["w"] + gap for p in placed}
        choices = []
        for x in options:
            if x + box["w"] + border > limit:
                continue
            y = border
            for p in sorted(placed, key=lambda v: v["y"]):
                if (
                    x + box["w"] + gap <= p["x"] + 0.001
                    or x >= p["x"] + p["w"] + gap - 0.001
                ):
                    continue
                if y + box["h"] + gap <= p["y"] + 0.001:
                    break
                y = max(y, p["y"] + p["h"] + gap)
            choices.append((y, x))
        y, x = min(choices)
        box.update(x=x, y=y)
        placed.append(box)
    return {
        "w": math.ceil(max(p["x"] + p["w"] for p in placed) + border),
        "h": math.ceil(max(p["y"] + p["h"] for p in placed) + border),
        "pieces": placed,
    }


def doc(layout, parts, annotated=False):
    w, h = layout["w"], layout["h"]
    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" viewBox="0 0 {w} {h}">'
    ]

    def transformed(points, b):
        x, y, X, Y = parts[b["key"]]["bbox"]
        return [
            (b["x"] + (X - px if b["flip"] else px - x), b["y"] + py - y)
            for px, py in points
        ]

    s.append(
        '<g id="CUT" fill="none" stroke="#72233a" stroke-width="0.18" stroke-linejoin="round">'
    )
    for b in layout["pieces"]:
        key = b["key"]
        s.append(
            f'<path id="{key}-{b["copy"]}" d="{path(transformed(parts[key]["cut"], b), True)}"/>'
        )
    s.append("</g>")
    if annotated:
        s.append('<g id="MARK" fill="none" stroke-width="0.26">')
        for b in layout["pieces"]:
            p = parts[b["key"]]
            for m in p["marks"]:
                color = (
                    "#466976" if m["kind"] in ("stitch", "notch", "trim") else "#9a744d"
                )
                dash = "none" if m["kind"] == "notch" else "2 1.4"
                s.append(
                    f'<path stroke="{color}" stroke-dasharray="{dash}" d="{path(transformed(m["p"], b))}"/>'
                )
            for x, y in transformed(p["centres"], b):
                s.append(
                    f'<path stroke="#99542f" d="M{x - 3:.2f} {y:.2f}h6 m-3 -3v6"/>'
                )
            for x, y in transformed(p["dots"], b):
                s.append(
                    f'<circle cx="{x:.2f}" cy="{y:.2f}" r=".33" stroke="none" fill="#365868"/>'
                )
        s.append(
            '</g><g id="LABELS" fill="#302a29" font-family="sans-serif" font-size="4.3" text-anchor="middle">'
        )
        for b in layout["pieces"]:
            x = b["x"] + b["w"] / 2
            y = b["y"] + b["h"] * 0.50
            if b["key"] == "G":
                y = b["y"] + 7
            if b["key"] in "BC":
                q = parts[b["key"]]["seam"]
                p = transformed(
                    [(sum(v[0] for v in q) / 4, sum(v[1] for v in q) / 4)], b
                )[0]
                x, y = p
            s.append(f'<text x="{x:.2f}" y="{y:.2f}">{b["key"]}{b["copy"]}</text>')
        s.append("</g>")
    return "\n".join(s + ["</svg>"]) + "\n"


def export(data):
    DOWNLOAD.mkdir(parents=True, exist_ok=True)
    layouts = {k: pack(data, k) for k in MATERIALS}
    for key, lay in layouts.items():
        for annotated, tag in [(False, "cut"), (True, "map")]:
            (DOWNLOAD / f"{key}-{tag}.svg").write_text(
                doc(lay, data["parts"], annotated)
            )
    (ASSETS / "layouts.json").write_text(
        json.dumps(tidy(layouts), separators=(",", ":")) + "\n"
    )
    return layouts


if __name__ == "__main__":
    for k, v in export(make()).items():
        print(k, v["w"], v["h"], len(v["pieces"]))
