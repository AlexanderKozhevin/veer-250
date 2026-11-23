"""Develop the sewing lines from the 3D shell. All coordinates are millimetres."""

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets"
DOWNLOAD = ROOT / "docs" / "downloads"
SA = 6
PITCH = 4
# Stations across the front, with the rear reflected about z=0. Y is up.
BOTTOM = [
    (-200, 56, 0),
    (-138, 17, 54),
    (-79, 0, 68),
    (79, 0, 68),
    (138, 17, 54),
    (200, 56, 0),
]
TOP = [
    (-123, 250, 0),
    (-93, 240, 24),
    (-65, 242, 31),
    (65, 242, 31),
    (93, 240, 24),
    (123, 250, 0),
]
MATERIALS = {
    "outer": "Основная кожа",
    "thin": "Тонкая кожа",
    "board": "Уплотнитель дна",
}


def add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def mul(a, k):
    return tuple(x * k for x in a)


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def lerp(a, b, t):
    return add(a, mul(sub(b, a), t))


def edges(poly):
    return list(zip(poly, poly[1:] + poly[:1]))


def signed_area(poly):
    return sum(cross(a, b) for a, b in edges(poly)) / 2


def bounds(poly):
    return [
        min(p[0] for p in poly),
        min(p[1] for p in poly),
        max(p[0] for p in poly),
        max(p[1] for p in poly),
    ]


def unit(v):
    return mul(v, 1 / math.hypot(*v))


def offset(poly, distance):
    """Intersect shifted edge lines. Distances are per edge or uniform, positive out."""
    pads = [distance] * len(poly) if isinstance(distance, (int, float)) else distance
    orientation = 1 if signed_area(poly) > 0 else -1
    lines = []
    for (a, b), d in zip(edges(poly), pads):
        v = unit(sub(b, a))
        lines.append((add(a, (v[1] * d * orientation, -v[0] * d * orientation)), v))
    result = []
    for i, (q, w) in enumerate(lines):
        p, v = lines[i - 1]
        result.append(
            q
            if abs(cross(v, w)) < 1e-10
            else add(p, mul(v, cross(sub(q, p), w) / cross(v, w)))
        )
    return result


def circle_intersections(a, b, ra, rb):
    v = sub(b, a)
    d = math.hypot(*v)
    u = mul(v, 1 / d)
    x = (ra * ra - rb * rb + d * d) / (2 * d)
    h = math.sqrt(max(0, ra * ra - x * x))
    foot = add(a, mul(u, x))
    delta = (-u[1] * h, u[0] * h)
    return add(foot, delta), sub(foot, delta)


def develop_quad(points):
    b0, b1, t1, t0 = points
    p0 = (0.0, 0.0)
    p1 = (math.dist(t0, t1), 0.0)
    bflat = circle_intersections(p0, p1, math.dist(t0, b0), math.dist(t1, b0))[0]
    candidates = circle_intersections(bflat, p1, math.dist(b0, b1), math.dist(t1, b1))
    sign = cross(sub(p1, bflat), sub(p0, bflat))
    opposite = next(
        p for p in candidates if cross(sub(p1, bflat), sub(p, bflat)) * sign < 0
    )
    return [bflat, opposite, p1, p0]


def cubic(p0, p1, p2, p3, n=20):
    return [
        tuple(
            (1 - t) ** 3 * a
            + 3 * (1 - t) ** 2 * t * b
            + 3 * (1 - t) * t * t * c
            + t**3 * d
            for a, b, c, d in zip(p0, p1, p2, p3)
        )
        for t in (i / n for i in range(1, n + 1))
    ]


def rounded_rect(w, h, r):
    p = []
    for cx, cy, a in [
        (w / 2 - r, -h / 2 + r, -90),
        (w / 2 - r, h / 2 - r, 0),
        (-w / 2 + r, h / 2 - r, 90),
        (-w / 2 + r, -h / 2 + r, 180),
    ]:
        p.extend(
            (
                cx + r * math.cos(math.radians(a + i * 90 / 8)),
                cy + r * math.sin(math.radians(a + i * 90 / 8)),
            )
            for i in range(9)
        )
    return p


def stitch_marks(a, b):
    n = max(1, round(math.dist(a, b) / PITCH))
    return [lerp(a, b, i / n) for i in range(n + 1)]


def line(p, kind, points):
    p["marks"].append({"kind": kind, "p": points})


def stitches(p, a, b):
    line(p, "stitch", [a, b])
    p["dots"].extend(stitch_marks(a, b))
    mid = lerp(a, b, 0.5)
    direction = unit(sub(b, a))
    normal = (-direction[1], direction[0])
    x, y, X, Y = p["bbox"]
    if dot(normal, sub(((x + X) / 2, (y + Y) / 2), mid)) > 0:
        normal = mul(normal, -1)
    line(p, "notch", [mid, add(mid, mul(normal, 3.5))])


def cross_mark(p, point):
    p["centres"].append(point)


def part(key, name, mat, qty, outline, note):
    return dict(
        key=key,
        name=name,
        material=mat,
        qty=qty,
        cut=outline,
        bbox=bounds(outline),
        area=abs(signed_area(outline)),
        marks=[],
        dots=[],
        centres=[],
        note=note,
    )


def wall_point(x, y):
    # Project the plane of the central face onto its flat pattern.
    return (x + 65, (242 - y) * math.hypot(1, 37 / 242))


def rear_z(y):
    return -(68 - 37 * y / 242)


# Centre line of the flap from the inside of the rear wall, over the mouth, to the front.
profile = [(-33.4, 213.0)]
for c1, c2, end in [
    ((-32.4, 221), (-31.6, 230), (-30.5, 236)),
    ((-29.8, 243), (-26, 246.5), (-19, 247.4)),
    ((-9, 248.8), (7, 249), (15, 247.5)),
    ((24, 246.7), (30.8, 245), (32.6, 238)),
    ((41, 225), (47.8, 197), (49.3, 177)),
    ((50.6, 157), (51.1, 142), (50.7, 133.5)),
]:
    profile.extend(cubic(profile[-1], c1, c2, end))
lengths = [0.0]
for a, b in zip(profile, profile[1:]):
    lengths.append(lengths[-1] + math.dist(a, b))
FL = lengths[-1]


def flap_position(s):
    import bisect

    i = max(0, min(len(profile) - 2, bisect.bisect_right(lengths, s) - 1))
    return lerp(
        profile[i], profile[i + 1], (s - lengths[i]) / (lengths[i + 1] - lengths[i])
    )


def flap_width(s):
    t = min(1, max(0, (s - 15) / 55))
    w = 45 + 46 * t * t * (3 - 2 * t)
    if s > FL - 35:
        w = 56 + 35 * math.sqrt(max(0, 1 - ((s - FL + 35) / 35) ** 2))
    return w


def handle_outline():
    # Left side of the outer and inner arch, from the foot to the crown.
    outer = [(-65, 209), (-65, 231)]
    outer += cubic(outer[-1], (-65, 239), (-62, 246), (-62, 260), 10)
    outer += cubic(outer[-1], (-62, 278), (-66, 350), (0, 350), 45)
    inner = [(-47, 209), (-47, 231)]
    inner += cubic(inner[-1], (-47, 241), (-52, 247), (-52, 260), 10)
    inner += cubic(inner[-1], (-52, 280), (-56, 339), (0, 339), 45)

    def arch(half):
        return half + [(-x, y) for x, y in half[-2::-1]]

    return [(x, 350 - y) for x, y in arch(outer) + list(reversed(arch(inner)))]


def make():
    parts = {}
    walls = {}
    seam_errors = []
    check_count = 0
    for key, i, name, qty, note in [
        (
            "A",
            2,
            "Центр корпуса",
            2,
            "Перед и спинка. Перенесите метки только для нужной стороны.",
        ),
        (
            "B",
            3,
            "Боковая панель",
            4,
            "Две зеркальные пары. Узкая сторона обращена к горловине.",
        ),
        (
            "C",
            4,
            "Крыло",
            4,
            "Две зеркальные пары. Внешние края двух крыльев образуют боковой шов.",
        ),
    ]:
        pts = [BOTTOM[i], BOTTOM[i + 1], TOP[i + 1], TOP[i]]
        q = develop_quad(pts)
        walls[key] = {"flat": q, "world": pts}
        p = part(key, name, "outer", qty, offset(q, [SA, SA, 0, SA]), note)
        p["seam"] = q
        for k in (0, 1, 3):
            a, b = edges(q)[k]
            stitches(p, a, b)
        p["edgeCodes"] = {
            "A": ["A", "1", "", "1"],
            "B": ["B", "2", "", "1"],
            "C": ["C", "3", "", "2"],
        }[key]
        parts[key] = p
    A = parts["A"]
    flap_rows = (6, 15)
    for s in flap_rows:
        y = flap_position(s)[1]
        line(A, "rear", [wall_point(-32, y), wall_point(32, y)])

    def footbox(x):
        return [
            (x - 4.5, 215),
            (x + 4.5, 215),
            (x + 4.5, 233),
            (x - 4.5, 233),
            (x - 4.5, 215),
        ]

    for x in (-56, 56):
        line(A, "rear", [wall_point(xx, y) for xx, y in footbox(x)])
    magnet_s = FL - 21
    cross_mark(A, wall_point(0, flap_position(magnet_s)[1]))
    # Unroll the folded base in strips, preserving depth parallel to each transverse fold.
    flat_x = [0.0]
    for a, b in zip(BOTTOM, BOTTOM[1:]):
        flat_x.append(flat_x[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    middle = flat_x[-1] / 2
    flat_x = [v - middle for v in flat_x]
    front = [(x, -p[2]) for x, p in zip(flat_x, BOTTOM)]
    back = [(x, p[2]) for x, p in zip(flat_x, BOTTOM)]
    q = front + back[-2:0:-1]
    D = part(
        "D",
        "Цельное дно",
        "outer",
        1,
        offset(q, SA),
        "Четыре поперечных сгиба поднимают концы дна. Сначала совместите середины длинных сторон с деталями A.",
    )
    D["seam"] = q
    for a, b in edges(q):
        stitches(D, a, b)
    for a, b in zip(front[1:-1], back[1:-1]):
        line(D, "fold", [a, b])
    D["edgeCodes"] = ["C", "B", "A", "B", "C", "C", "B", "A", "B", "C"]
    parts["D"] = D
    # Spacing close to the tangent of the rounded flap tip needs denser arc samples.
    sample_s = [(FL - 35) * i / 72 for i in range(73)] + [
        FL - 35 + 35 * math.sin(i * math.pi / 120) for i in range(1, 61)
    ]
    flap = [(flap_width(s), s) for s in sample_s]
    outline = flap + [(-x, s) for x, s in reversed(flap)]
    E = part(
        "E",
        "Лицевая сторона клапана",
        "outer",
        1,
        outline,
        "Урез готового клапана. Склейте с F на объёмной форме, затем прошейте по периметру.",
    )
    line(E, "stitch", offset(outline, -3) + [offset(outline, -3)[0]])
    for s in flap_rows:
        line(E, "rear", [(-32, s), (32, s)])
    for s in (lengths[40], lengths[80]):
        line(E, "bend", [(-flap_width(s) + 3, s), (flap_width(s) - 3, s)])
    parts["E"] = E
    F = part(
        "F",
        "Изнанка клапана",
        "thin",
        1,
        offset(outline, 3),
        "По краю дан запас 3 мм. После склейки на форме подрежьте его по лицевой детали E.",
    )
    line(F, "trim", outline + [outline[0]])
    cross_mark(F, (0, magnet_s))
    parts["F"] = F
    G = part(
        "G",
        "Арочная ручка",
        "outer",
        2,
        handle_outline(),
        "Склейте две половины изнанками. Тянущее усилие принимают обе пришитые к спинке ножки.",
    )
    inn = offset(G["cut"], -2.5)
    line(G, "stitch", inn + inn[:1])
    for x in (-56, 56):
        line(G, "rear", [(xx, 350 - y) for xx, y in footbox(x)])
    parts["G"] = G
    parts["H"] = part(
        "H",
        "Усилитель ручки",
        "outer",
        2,
        rounded_rect(26, 36, 4),
        "По одному с изнанки спинки под каждой ножкой. Прямоугольник крепления прошивает все слои.",
    )
    parts["I"] = part(
        "I",
        "Вставка дна",
        "board",
        1,
        rounded_rect(142, 116, 9),
        "Вклейте на плоский центр дна после выворачивания. До ближайшего сгиба останется 8 мм.",
    )
    circ = [
        (18 * math.cos(i * math.tau / 72), 18 * math.sin(i * math.tau / 72))
        for i in range(72)
    ]
    parts["J"] = part(
        "J",
        "Накладка кнопки",
        "thin",
        2,
        circ,
        "Первая под шайбу передней половины кнопки, вторая закрывает крепёж изнутри.",
    )

    # Check the two independent developments of every sewn interface in the assembled shell.
    def check(edge_a, edge_b):
        nonlocal check_count
        la, lb = math.dist(*edge_a), math.dist(*edge_b)
        seam_errors.append(abs(la - lb))
        assert abs(la - lb) < 1e-6 and len(stitch_marks(*edge_a)) == len(
            stitch_marks(*edge_b)
        )
        check_count += 1

    def e(key, index):
        return edges(walls[key]["flat"])[index]

    for _ in range(4):
        check(e("A", 1), e("B", 3))
        check(e("B", 1), e("C", 3))
    for _ in range(2):
        check(e("C", 1), e("C", 1))
    for key, side in zip(D["edgeCodes"], edges(q)):
        check(e(key, 0), side)
    for key, p in parts.items():
        p["dots"] = list({(round(x, 5), round(y, 5)) for x, y in p["dots"]})
        p["dots"].sort()
    return dict(
        parts=parts,
        walls=walls,
        top=TOP,
        bottom=BOTTOM,
        flatX=flat_x,
        flap=[[s, z, y, flap_width(s)] for s, (z, y) in zip(lengths, profile)],
        magnetS=magnet_s,
        materials=MATERIALS,
        check={
            "pairs": check_count,
            "maxError": max(seam_errors),
            "allowance": SA,
            "pitch": PITCH,
        },
        sizes={"body": 250, "total": 350, "width": 400, "depth": 136},
    )


def tidy(obj):
    if isinstance(obj, float):
        return round(obj, 4)
    if isinstance(obj, (list, tuple)):
        return [tidy(v) for v in obj]
    if isinstance(obj, dict):
        return {k: tidy(v) for k, v in obj.items()}
    return obj


if __name__ == "__main__":
    data = make()
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "pattern.json").write_text(
        json.dumps(tidy(data), ensure_ascii=False, separators=(",", ":")) + "\n"
    )
    print("Paired seams:", data["check"])
    for k, p in data["parts"].items():
        x, y, X, Y = p["bbox"]
        print(
            k,
            p["qty"],
            round(X - x, 1),
            round(Y - y, 1),
            round(p["area"] / 100, 1),
            "cm²",
        )
