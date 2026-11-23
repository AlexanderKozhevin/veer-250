"""Check cut sheets and printed scale, then make the downloadable workshop kit."""

from collections import Counter, defaultdict
from itertools import combinations
import math
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo
from pypdf import PdfReader
from pattern import DOWNLOAD, make, edges, stitch_marks
from layout import pack


def verify_seams(data):
    shared = defaultdict(list)

    def record(world, flat):
        length = math.dist(*flat)
        assert abs(math.dist(*world) - length) < 1e-4
        shared[tuple(sorted(world))].append((length, len(stitch_marks(*flat))))

    for z_sign in (-1, 1):
        for key in "ABC":
            form = data["walls"][key]
            for x_sign in (1,) if key == "A" else (-1, 1):
                points = [(x * x_sign, y, z * z_sign) for x, y, z in form["world"]]
                for i in (0, 1, 3):
                    record(edges(points)[i], edges(form["flat"])[i])
    base = data["bottom"] + [(x, y, -z) for x, y, z in data["bottom"][-2:0:-1]]
    for pair, flat in zip(edges(base), edges(data["parts"]["D"]["seam"])):
        record(pair, flat)
    assert len(shared) == 20
    for entries in shared.values():
        assert (
            len(entries) == 2
            and abs(entries[0][0] - entries[1][0]) < 1e-5
            and entries[0][1] == entries[1][1]
        )


def verify_layout(data):
    ns = {"s": "http://www.w3.org/2000/svg"}
    counts = Counter()
    for material in data["materials"]:
        lay = pack(data, material)
        root = ET.parse(DOWNLOAD / (material + "-cut.svg")).getroot()
        assert (
            root.get("width") == f"{lay['w']}mm"
            and root.get("height") == f"{lay['h']}mm"
        )
        paths = root.findall("s:g/s:path", ns)
        assert len(paths) == len(lay["pieces"])
        for item, p in zip(lay["pieces"], paths):
            key = item["key"]
            counts[key] += 1
            attr = p.get("d")
            assert attr.endswith(" Z") and attr.count("M") == 1
            points = [
                tuple(map(float, pt.split())) for pt in re.split(r"\s*L", attr[1:-2])
            ]
            original = data["parts"][key]
            x0, y0, X, Y = original["bbox"]
            expected = [
                (item["x"] + (X - x if item["flip"] else x - x0), item["y"] + y - y0)
                for x, y in original["cut"]
            ]
            assert (
                len(points) == len(expected)
                and max(math.dist(a, b) for a, b in zip(points, expected)) < 0.00072
            )
            assert all(0 < x < lay["w"] and 0 < y < lay["h"] for x, y in points)
        for a, b in combinations(lay["pieces"], 2):
            assert (
                a["x"] + a["w"] <= b["x"]
                or b["x"] + b["w"] <= a["x"]
                or a["y"] + a["h"] <= b["y"]
                or b["y"] + b["h"] <= a["y"]
            )
    assert counts == Counter({k: p["qty"] for k, p in data["parts"].items()})


def verify_pdf():
    pt = 72 / 25.4
    pdf = PdfReader(DOWNLOAD / "veer-250-a4.pdf")
    assert len(pdf.pages) == 10
    for i, p in enumerate(pdf.pages):
        w, h = (297, 210) if i in (4, 5) else (210, 297)
        assert (
            abs(float(p.mediabox.width) / pt - w) < 0.002
            and abs(float(p.mediabox.height) / pt - h) < 0.002
        )
    verify_calibration(pdf.pages[0])
    a3 = PdfReader(DOWNLOAD / "veer-250-a3.pdf")
    assert len(a3.pages) == 4
    verify_calibration(a3.pages[0])
    parts = make()["parts"]
    for page, ids in zip(a3.pages, ["GIHJ", "ABC", "D", "EF"]):
        assert (
            abs(float(page.mediabox.width) / pt - 420) < 0.002
            and abs(float(page.mediabox.height) / pt - 297) < 0.002
        )
        contours = printed_cuts(page)
        assert len(contours) == len(ids)
        for shape, key in zip(contours, ids):
            reference = parts[key]["cut"]
            assert len(shape) == len(reference)
            assert (
                max(
                    abs(math.dist(*a) - math.dist(*b))
                    for a, b in zip(edges(shape), edges(reference))
                )
                < 0.002
            )
            assert all(8 < x < 412 and 8 < y < 289 for x, y in shape)
    assert len(PdfReader(DOWNLOAD / "veer-250-guide.pdf").pages) == 6


def verify_calibration(page):
    pt = 72 / 25.4
    paths = []
    current = []
    for operands, op in page.get_contents().operations:
        if op == b"m":
            current = [tuple(map(float, operands))]
        if op == b"l":
            current.append(tuple(map(float, operands)))
        if op == b"S":
            paths.append(current)
            current = []

    def length(p):
        return math.dist(*p) / pt

    assert any(
        len(q) == 4 and all(abs(length(edge) - 50) < 0.002 for edge in edges(q))
        for q in paths
    )
    assert any(len(q) == 2 and abs(length(q) - 100) < 0.002 for q in paths)


def printed_cuts(page):
    # ReportLab composes the rotation into a single matrix; stroke width distinguishes cut from marks.
    scale = 72 / 25.4
    matrix = (1, 0, 0, 1, 0, 0)
    stack = []
    contours = []
    points = []
    stroke = 0
    closed = False
    for args, op in page.get_contents().operations:
        if op == b"q":
            stack.append((matrix, stroke))
        elif op == b"Q":
            matrix, stroke = stack.pop()
        elif op == b"cm":
            a, b, c, d, e, f = map(float, args)
            A, B, C, D, E, F = matrix
            matrix = (
                A * a + C * b,
                B * a + D * b,
                A * c + C * d,
                B * c + D * d,
                A * e + C * f + E,
                B * e + D * f + F,
            )
        elif op == b"w":
            stroke = float(args[0]) / scale
        elif op in (b"m", b"l"):
            if op == b"m":
                points = []
                closed = False
            a, b, c, d, e, f = matrix
            x, y = map(float, args)
            points.append(((a * x + c * y + e) / scale, (b * x + d * y + f) / scale))
        elif op == b"h":
            closed = True
        elif op == b"S" and closed and abs(stroke - 0.34) < 0.0001:
            contours.append(points)
            closed = False
    return contours


def bundle():
    layout_note = """ВЕЕР / 250 — комплект мастерской

01_Лекала_A3.pdf — 4 альбомных листа, все шаблоны целиком.
02_Лекала_A4.pdf — 10 листов. Печать 100 %. На листе 1 измерьте квадрат 50 × 50 мм и линейку 100 мм.
03_Сборка.pdf — материалы и восемь шагов сборки.

SVG-CUT — только замкнутые контуры в натуральную величину, все копии уже разложены.
SVG-MAP — те же листы с обозначениями, линиями шва, контрольными метками и сгибами. Используйте для переноса разметки.
outer — основная кожа, 16 деталей. thin — тонкая кожа, 3 детали. board — уплотнитель, 1 деталь.
Единицы при импорте — миллиметры. Габарит детали I для проверки импорта — 142 × 116 мм.

Корпус 250 мм, с ручкой 350 мм, ширина 400 мм, глубина 136 мм.
Это реконструкция по фотографии. Фактическая посадка зависит от кожи и фурнитуры. Сначала соберите бумажный макет.

Модель и исходники
https://alexanderkozhevin.github.io/veer-250/
https://github.com/AlexanderKozhevin/veer-250
"""
    files = {
        "Начните здесь.txt": layout_note.encode(),
        "01_Лекала_A3.pdf": (DOWNLOAD / "veer-250-a3.pdf").read_bytes(),
        "02_Лекала_A4.pdf": (DOWNLOAD / "veer-250-a4.pdf").read_bytes(),
        "03_Сборка.pdf": (DOWNLOAD / "veer-250-guide.pdf").read_bytes(),
    }
    for k in ("outer", "thin", "board"):
        for tag in ("cut", "map"):
            files[f"SVG-{tag.upper()}/{k}-{tag}.svg"] = (
                DOWNLOAD / f"{k}-{tag}.svg"
            ).read_bytes()
    target = DOWNLOAD / "veer-250-kit.zip"
    with ZipFile(target, "w") as z:
        for name, content in files.items():
            entry = ZipInfo(name, (2026, 11, 23, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            z.writestr(entry, content)
    with ZipFile(target) as z:
        assert z.testzip() is None and len(z.namelist()) == 10


if __name__ == "__main__":
    model = make()
    verify_seams(model)
    verify_layout(model)
    verify_pdf()
    bundle()
    print(
        "20 paired seams, 20 full-size cut contours, A3/A4 calibration, all ten uncut A3 templates and 10 kit entries verified."
    )
