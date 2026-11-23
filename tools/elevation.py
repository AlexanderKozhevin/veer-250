"""Generate the orthographic fallback from the same sewing geometry."""

from pattern import make, ASSETS
from layout import path

d = make()
parts = d["parts"]


def project(p):
    return (240 + p[0], 373 - p[1])


def outline(ps, fill, stroke="#571d32", sw=1.1):
    return f'<path d="{path(ps, True)}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"/>'


s = [
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 407"><defs><linearGradient id="wine" x2=".3" y2="1" gradientUnits="objectBoundingBox"><stop stop-color="#823b4a"/><stop offset=".4" stop-color="#652638"/><stop offset="1" stop-color="#3d1726"/></linearGradient><linearGradient id="flap" x2=".18" y2="1"><stop stop-color="#97495b"/><stop offset=".42" stop-color="#772d41"/><stop offset="1" stop-color="#4c2032"/></linearGradient><linearGradient id="brass" x2=".3" y2="1"><stop stop-color="#f0d99d"/><stop offset="1" stop-color="#ae8456"/></linearGradient></defs>'
]
s.append('<ellipse cx="240" cy="375" rx="123" ry="5" fill="#a7978f" opacity=".4"/>')
s.append(outline([project((x, 350 - y)) for x, y in parts["G"]["cut"]], "url(#wine)"))
for i in range(5):
    b, t = d["bottom"], d["top"]
    ps = [project(a) for a in [b[i], b[i + 1], t[i + 1], t[i]]]
    s.append(outline(ps, ["#783849", "#69293b", "url(#wine)", "#612538", "#722f41"][i]))
    s.append(
        f'<path d="{path([ps[0], ps[3]])}" transform="translate(2)" stroke="#c88b90" fill="none" stroke-width=".85" stroke-dasharray="2 2"/>'
    )
visible = [(w, y) for _, z, y, w in d["flap"] if z > 14]
s.append(
    outline(
        [project(p) for p in visible] + [project((-x, y)) for x, y in visible[::-1]],
        "url(#flap)",
    )
)
s.append(
    '<rect x="215" y="230" width="50" height="10" rx="2" fill="url(#brass)" stroke="#baa47d"/></svg>'
)
(ASSETS / "elevation.svg").write_text("".join(s))
