"""Render vector paper templates and an illustrated workshop booklet. Distances in mm."""

import json
import math
import os
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pattern import ROOT, DOWNLOAD, make, edges, lerp, wall_point

candidates = [
    Path(os.environ.get("PATTERN_FONT_DIR", "/usr/share/fonts/truetype/dejavu")),
    Path("/System/Library/Fonts/Supplemental"),
]
for family, names in [
    ("Sans", ["DejaVuSans.ttf", "Arial.ttf"]),
    ("Bold", ["DejaVuSans-Bold.ttf", "Arial Bold.ttf"]),
    ("Serif", ["DejaVuSerif.ttf", "Georgia.ttf"]),
]:
    f = next((d / n for d in candidates for n in names if (d / n).is_file()), None)
    if not f:
        raise RuntimeError(
            "Set PATTERN_FONT_DIR to a directory containing DejaVu Sans, Sans Bold and Serif TTF files."
        )
    pdfmetrics.registerFont(TTFont(family, str(f)))

INK = "#282322"
WINE = "#70253d"
MUTE = "#625d57"
FAINT = "#d7cfc3"
BLUE = "#355f6d"
GOLD = "#9a6031"
PAPER = "#f2ede5"


class Sheet:
    def __init__(self, filename, title):
        self.c = canvas.Canvas(
            str(DOWNLOAD / filename), pageCompression=1, invariant=True
        )
        self.c.setTitle(title)
        self.c.setAuthor("Веер / мастерская выкройки")

    def page(self, w=210, h=297):
        self.w, self.h = w, h
        self.c.setPageSize((w * mm, h * mm))

    def txt(self, x, y, t, size=9, font="Sans", color=INK, align="left"):
        self.c.setFont(font, size)
        self.c.setFillColor(HexColor(color))
        getattr(
            self.c,
            {
                "left": "drawString",
                "right": "drawRightString",
                "center": "drawCentredString",
            }[align],
        )(x * mm, (self.h - y) * mm, t)

    def path(self, ps, color=INK, width=0.24, dash=None, close=False, fill=None):
        self.c.setStrokeColor(HexColor(color))
        self.c.setLineWidth(width * mm)
        self.c.setLineJoin(1)
        self.c.setLineCap(1)
        self.c.setDash([v * mm for v in dash] if dash else [])
        p = self.c.beginPath()
        p.moveTo(ps[0][0] * mm, (self.h - ps[0][1]) * mm)
        for x, y in ps[1:]:
            p.lineTo(x * mm, (self.h - y) * mm)
        if close:
            p.close()
        if fill:
            self.c.setFillColor(HexColor(fill))
        self.c.drawPath(p, stroke=1, fill=int(bool(fill)))

    def line(self, x, y, X, Y, **kw):
        self.path([(x, y), (X, Y)], **kw)

    def rect(self, x, y, w, h, **kw):
        self.path([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], close=True, **kw)

    def dot(self, x, y, r=0.27, col=BLUE):
        self.c.setFillColor(HexColor(col))
        self.c.circle(x * mm, (self.h - y) * mm, r * mm, stroke=0, fill=1)

    def cross(self, x, y, r=3, col=GOLD):
        self.line(x - r, y, x + r, y, color=col)
        self.line(x, y - r, x, y + r, color=col)

    def wrap(self, x, y, t, width, size=9.5, leading=4.7, font="Sans", color=INK):
        words = t.split()
        line = ""
        for word in words:
            nxt = (line + " " + word).strip()
            if pdfmetrics.stringWidth(nxt, font, size) > width * mm and line:
                self.txt(x, y, line, size, font, color)
                y += leading
                line = word
            else:
                line = nxt
        if line:
            self.txt(x, y, line, size, font, color)
            y += leading
        return y

    def header(self, title, index, sub=None):
        self.txt(11, 11, title, 13, "Bold")
        self.txt(self.w - 11, 10, index, 8, "Sans", MUTE, "right")
        if sub:
            self.txt(11, 18.4, sub, 8, "Sans", MUTE)
        self.line(11, 22, self.w - 11, 22, color=FAINT, width=0.2)

    def footer(self, label):
        self.line(11, self.h - 12, self.w - 11, self.h - 12, color=FAINT, width=0.18)
        self.txt(11, self.h - 6, label, 7.5, "Sans", MUTE)
        self.txt(self.w - 11, self.h - 6, "ВЕЕР   /   250", 7.5, "Bold", WINE, "right")

    def done(self):
        self.c.showPage()


data = make()
parts = data["parts"]
book = json.loads((ROOT / "src/workshop.json").read_text())
styles = {
    "notch": (BLUE, None),
    "stitch": (BLUE, [1.7, 1.15]),
    "fold": (GOLD, [5, 1.4, 1, 1.4]),
    "bend": (GOLD, [5, 1.4, 1, 1.4]),
    "rear": (GOLD, [1.1, 0.9]),
    "trim": (BLUE, [3, 1.3]),
}


def piece(sh, key, at, zoom=1, detail=True, code=True):
    p = parts[key]
    x, y, X, Y = p["bbox"]
    ox, oy = at

    def tr(q):
        return (ox + (q[0] - x) * zoom, oy + (q[1] - y) * zoom)

    sh.path([tr(q) for q in p["cut"]], WINE, 0.34, close=True)
    for m in p["marks"]:
        c, d = styles[m["kind"]]
        sh.path([tr(q) for q in m["p"]], c, 0.20, d)
    if detail:
        for pt in p["dots"]:
            sh.dot(*tr(pt), r=0.28)
    for pt in p["centres"]:
        sh.cross(*tr(pt), r=3 if detail else 1.5)
    if code:
        if key in "ABC":
            q = p["seam"]
            cx = sum(qi[0] for qi in q) / 4
            cy = sum(qi[1] for qi in q) / 4
        elif key == "G":
            cx = 0
            cy = 8.5
        else:
            cx = (x + X) / 2
            cy = (y + Y) / 2
        xx, yy = tr((cx, cy))
        if key == "D":
            yy += 9 * zoom
        sh.txt(xx, yy, key, 15 if detail else 8, "Bold", WINE, "center")
    if detail and "edgeCodes" in p:
        for (a, b), label in zip(edges(p["seam"]), p["edgeCodes"]):
            if not label:
                continue
            m = lerp(a, b, 0.48)
            ctr = ((x + X) / 2, (y + Y) / 2)
            dx, dy = ctr[0] - m[0], ctr[1] - m[1]
            l = math.hypot(dx, dy) or 1
            xx, yy = tr((m[0] + 6 * dx / l, m[1] + 6 * dy / l))
            sh.txt(xx, yy, label, 8, "Bold", BLUE, "center")
    if detail and key == "A":
        xx, yy = tr(p["centres"][0])
        sh.txt(xx, yy + 7, "ПЕРЕД · кнопка", 7, "Sans", GOLD, "center")
        xx, yy = tr(wall_point(0, 198))
        sh.txt(xx, yy, "СПИНКА · крепления", 7, "Sans", GOLD, "center")
    return tr


def ruler(sh, x, y):
    sh.line(x, y, x + 100, y, width=0.4)
    for t in range(0, 101, 5):
        h = 4 if t % 10 == 0 else 2
        sh.line(x + t, y, x + t, y - h, width=0.22)
    sh.txt(x, y + 5, "0", 7)
    sh.txt(x + 100, y + 5, "100 мм", 7, align="right")


def seam_glyphs(sh, x, y):
    info = [
        ("Линия реза", WINE, None),
        ("Линия шва и точки прокола", BLUE, [1.7, 1.15]),
        ("Сгиб или зона плавного изгиба", GOLD, [5, 1.4, 1, 1.4]),
        ("Крепление на спинке", GOLD, [1.1, 0.9]),
    ]
    for i, (t, col, d) in enumerate(info):
        yy = y + i * 8
        sh.line(x, yy, x + 17, yy, color=col, width=0.30, dash=d)
        sh.txt(x + 22, yy + 1, t, 8.5)
    sh.cross(x + 8.5, y + 32, r=2.4)
    sh.txt(x + 22, y + 33, "Центр кнопки, сверить на сборке", 8.5)


def templates():
    sh = Sheet("veer-250-a4.pdf", "Веер 250 — выкройка A4 в натуральную величину")
    sh.page()
    sh.header("Выкройка в натуральную величину", "ЛИСТ 01 / 10")
    sh.txt(13, 44, "Веер / 250", 30, "Serif", WINE)
    sh.txt(
        14,
        56,
        "Корпус 250 мм   ·   с ручкой 350 мм   ·   ширина 400 мм   ·   глубина 136 мм",
        9,
    )
    sh.wrap(
        14,
        70,
        "Выберите A4 и «Фактический размер» (100 %). Начните с этого листа. Измерьте квадрат по двум осям и линейку внизу. При расхождении отключите подгонку страницы и повторите печать.",
        178,
        10,
        5,
    )
    sh.txt(14, 98, "Листы и детали", 12, "Bold")
    entries = [
        ("02", "A · центр корпуса ×2"),
        ("03", "B · боковая панель ×4"),
        ("04", "C · крыло ×4"),
        ("05 + 06", "D · цельное дно ×1"),
        ("07", "E · наружный клапан ×1"),
        ("08", "F · изнанка клапана ×1"),
        ("09", "G · ручка ×2"),
        ("10", "H ×2, I ×1, J ×2 · усилители"),
    ]
    for i, (n, t) in enumerate(entries):
        x = 14 if i < 4 else 107
        yy = 109 + (i % 4) * 8
        sh.txt(x, yy, n, 8, "Bold", WINE)
        sh.txt(x + 15, yy, t, 8.3)
    sh.line(14, 143, 196, 143, color=FAINT)
    seam_glyphs(sh, 14, 154)
    sh.wrap(
        114,
        155,
        "Припуск 6 мм уже включён у A–D. Внешний контур определяет край детали. Буквы на дне показывают, какую панель пришить. Цифры 1–3 задают парные боковые швы. Короткая поперечная метка — середина шва.",
        80,
        9,
        4.7,
    )
    sh.rect(16, 211, 50, 50, color=INK, width=0.24)
    sh.txt(41, 238, "50 × 50 мм", 10, "Bold", INK, "center")
    sh.txt(92, 224, "Контроль длины", 11, "Bold")
    ruler(sh, 92, 245)
    sh.footer("Печать 100 %   ·   A4   ·   положение листов 5 и 6 — альбомное")
    sh.done()
    subtitles = {
        "A": "2 детали · Перед и спинка. Крепления спинки показаны охрой.",
        "B": "4 детали · 2 обычные и 2 зеркальные. Шов 1 к центру A, шов 2 к крылу C.",
        "C": "4 детали · 2 обычные и 2 зеркальные. Шов 2 к панели B, шов 3 к другому крылу C.",
        "E": "1 деталь из основной кожи · Две поперечные метки обозначают плавный перегиб.",
        "F": "1 деталь из тонкой кожи · Запас 3 мм подрезать по E после склейки.",
        "G": "2 детали из основной кожи · Совместить изнанками и прошить арку в 2,5 мм от края.",
    }
    for n, k in [
        (2, "A"),
        (3, "B"),
        (4, "C"),
        (5, "D"),
        (6, "D"),
        (7, "E"),
        (8, "F"),
        (9, "G"),
        (10, "H"),
    ]:
        if k == "D":
            sh.page(297, 210)
            side = "левая" if n == 5 else "правая"
            sh.header(
                f"D   /   Цельное дно, {side} половина",
                f"ЛИСТ {n:02d} / 10",
                "Совместите кресты 1 и 2 с соседним листом, склейте и вырежьте одно цельное дно.",
            )
            # Both pages use the same global slab with a 20 mm overlap around x=0.
            xmin, ymin, xmax, ymax = parts[k]["bbox"]
            half = (xmax - xmin) / 2
            centre = 260 if n == 5 else 37
            width = half + 10
            left = centre - half if n == 5 else centre - 10
            y = 30
            sh.c.saveState()
            clip = sh.c.beginPath()
            clip.rect(left * mm, (210 - y - 151) * mm, width * mm, 151 * mm)
            sh.c.clipPath(clip, stroke=0)
            piece(sh, k, (centre - half, y), code=False)
            sh.c.restoreState()
            for idx, yy in enumerate((43, 168), 1):
                sh.cross(centre, yy, 3.7, INK)
                sh.txt(centre + 5, yy + 1.5, str(idx), 8, "Bold")
            sh.line(centre, 33, centre, 176, color=MUTE, width=0.17, dash=[0.6, 1.4])
            sh.txt(centre, 189, "Линия совмещения", 7, "Sans", MUTE, "center")
        elif k == "H":
            sh.page()
            sh.header(
                "H, I, J   /   Усилители",
                "ЛИСТ 10 / 10",
                "Каждый контур напечатан в натуральную величину.",
            )
            piece(sh, "I", (34, 42))
            sh.txt(34, 166, "I   /   Вставка дна · 142 × 116 мм · 1 деталь", 9, "Bold")
            piece(sh, "H", (40, 187))
            piece(sh, "J", (129, 187))
            sh.txt(53, 234, "H · 26 × 36 мм", 9, "Bold", align="center")
            sh.txt(53, 241, "2 из основной кожи", 8, align="center")
            sh.txt(147, 234, "J · Ø 36 мм", 9, "Bold", align="center")
            sh.txt(147, 241, "2 из тонкой кожи", 8, align="center")
        else:
            p = parts[k]
            x, y, X, Y = p["bbox"]
            w, h = X - x, Y - y
            sh.page()
            sh.header(f"{k}   /   {p['name']}", f"ЛИСТ {n:02d} / 10", subtitles[k])
            ox = (210 - w) / 2
            oy = 26 + (253 - h) / 2
            piece(sh, k, (ox, oy))
            if k == "G":
                sh.wrap(
                    35,
                    244,
                    "Прямоугольники на ножках совпадают с метками на задней A. Под каждый изнутри положите усилитель H.",
                    145,
                )
        sh.footer("Натуральная величина   ·   размеры в миллиметрах")
        sh.done()
    sh.c.save()


def mini(sh, key, x, y, w, h, code=False):
    box = parts[key]["bbox"]
    s = min(w / (box[2] - box[0]), h / (box[3] - box[1]))
    piece(
        sh,
        key,
        (x + (w - (box[2] - box[0]) * s) / 2, y + (h - (box[3] - box[1]) * s) / 2),
        s,
        False,
        code,
    )


def front(sh, cx, baseline, scale):
    def pt(x, y):
        return (cx + x * scale, baseline - y * scale)

    # Draw the five sewn panels and the distinct flap in elevation.
    b = data["bottom"]
    t = data["top"]
    for i in range(5):
        ps = [b[i], b[i + 1], t[i + 1], t[i]]
        sh.path(
            [pt(x, y) for x, y, z in ps],
            WINE,
            0.35,
            close=True,
            fill=["#eee0dd", "#e3c9c7", "#f1e3dd", "#e3c9c7", "#eee0dd"][i],
        )
    sh.path(
        [pt(x, 350 - y) for x, y in parts["G"]["cut"]],
        WINE,
        0.32,
        close=True,
        fill="#ecdcd6",
    )
    visible = [(w, y) for _, z, y, w in data["flap"] if z > 12]
    sh.path(
        [pt(x, y) for x, y in visible] + [pt(-x, y) for x, y in visible[::-1]],
        WINE,
        0.38,
        close=True,
        fill="#e5cbc8",
    )
    sh.rect(*pt(-25, 145), 50 * scale, 9 * scale, color=GOLD, fill="#c5a16b")
    return pt


def technical_diagram(sh, step, x, y, w=46, h=45):
    if step == 0:
        sh.rect(x + 8, y + 2, 26, 26, color=WINE)
        sh.txt(x + 21, y + 18, "50", 10, "Serif", WINE, "center")
        sh.line(x + 2, y + 36, x + 42, y + 36, color=BLUE)
        for i in range(11):
            sh.line(
                x + 2 + i * 4, y + 36, x + 2 + i * 4, y + 32 + (i % 2) * 2, color=BLUE
            )
    elif step == 1:
        front(sh, x + w / 2, y + h, 0.105)
    elif step == 2:
        mini(sh, "B", x, y + 1, 21, 40, True)
        mini(sh, "C", x + 23, y + 1, 22, 40, True)
    elif step == 3:
        mini(sh, "G", x + 3, y, 39, 40)
        sh.txt(x + 24, y + 44, "G  +  H", 7, "Bold", WINE, "center")
    elif step == 4:
        mini(sh, "F", x + 2, y + 3, 30, 37)
        mini(sh, "E", x + 11, y, 30, 37)
    elif step == 5:
        for j, k in enumerate("CBABC"):
            mini(sh, k, x + j * 9, y + 4, 9, 35, True)
    elif step == 6:
        mini(sh, "D", x, y + 5, w, 26)
        sh.txt(
            x + w / 2, y + 37, "C  ·  B  ·  A  ·  B  ·  C", 7, "Bold", WINE, "center"
        )
    else:
        front(sh, x + w / 2, y + h, 0.11)


def guide():
    sh = Sheet("veer-250-guide.pdf", "Веер 250 — материалы и иллюстрированная сборка")
    sh.page()
    sh.header("Мастерская выкройки", "РУКОВОДСТВО   /   01")
    sh.txt(15, 47, "Сумка «Веер»", 31, "Serif", WINE)
    sh.txt(16, 60, "Материалы, раскрой и сборка вручную", 12)
    pt = front(sh, 107, 194, 0.295)
    for x, y1, y2, label in [(177, 0, 250, "250 мм"), (29, 0, 350, "350 мм")]:
        yy1 = pt(0, y1)[1]
        yy2 = pt(0, y2)[1]
        sh.line(x, yy1, x, yy2, color=MUTE, width=0.2)
        sh.line(x - 2, yy1, x + 2, yy1, color=MUTE)
        sh.line(x - 2, yy2, x + 2, yy2, color=MUTE)
        sh.txt(
            x - 3 if x < 50 else x + 3,
            (yy1 + yy2) / 2,
            label,
            7.5,
            "Bold",
            MUTE,
            "right" if x < 50 else "left",
        )
    sh.line(*pt(-200, -24), *pt(200, -24), color=MUTE)
    sh.txt(107, 208, "400 мм", 8, "Bold", MUTE, "center")
    sh.wrap(
        16,
        225,
        "Десять панелей сходятся к узкой горловине. Цельное дно сгибается в четырёх местах и приподнимает боковые крылья. Нагрузка с ручки уходит через две ножки в усиленную спинку.",
        179,
        11,
        5.7,
    )
    sh.wrap(
        16,
        254,
        "Рабочая реконструкция по одному фронтальному фото. Глубина 136 мм, устройство дна и креплений выбраны для этой версии. Длины всех 20 пар стачных швов проверены расчётом. Посадку на коже проверьте макетом.",
        179,
        9,
        4.6,
        color=MUTE,
    )
    sh.footer("Модель и размер   ·   размеры без поправки на толщину кожи")
    sh.done()
    sh.page()
    sh.header("Материалы и раскрой", "РУКОВОДСТВО   /   02")
    y = 39
    for name, spec, desc in book["materials"]:
        sh.txt(14, y, name, 11, "Bold")
        sh.txt(196, y, spec, 8.5, "Sans", WINE, "right")
        y = sh.wrap(14, y + 6, desc, 181, 8.8, 4.25) + 5
    sh.txt(14, y + 2, "Что вырезать", 13, "Serif", WINE)
    y += 12
    for i, (k, p) in enumerate(parts.items()):
        col = i // 5
        row = i % 5
        xx = 14 + 94 * col
        yy = y + row * 6.5
        sh.txt(xx, yy, k, 8, "Bold", WINE)
        sh.txt(xx + 7, yy, p["name"], 8)
        sh.txt(xx + 83, yy, "× " + str(p["qty"]), 8, "Bold", align="right")
    y += 42
    sh.txt(14, y, "Инструменты", 11, "Bold")
    y = sh.wrap(14, y + 7, book["tools"], 181, 9, 4.5) + 4
    sh.wrap(
        14,
        y,
        "Карты SVG содержат все 20 экземпляров. CUT — замкнутые контуры реза, MAP — тот же расклад с разметкой. Единицы импорта — мм. Расход учитывает промежутки и выбор участков шкуры.",
        180,
        8.5,
        4.4,
        color=MUTE,
    )
    sh.footer("Основную кожу подбирайте по пробному сгибу и шву")
    sh.done()
    for spread in range(4):
        sh.page()
        sh.header("Последовательность сборки", f"РУКОВОДСТВО   /   {spread + 3:02d}")
        for row in range(2):
            i = spread * 2 + row
            y = 40 + row * 122
            title, first, last = book["steps"][i]
            sh.txt(14, y, f"{i + 1:02d}", 11, "Bold", GOLD)
            sh.txt(30, y, title, 17, "Serif", WINE)
            technical_diagram(sh, i, 14, y + 17, 46, 48)
            stop = sh.wrap(70, y + 14, first, 124, 10, 5.25)
            stop = sh.wrap(70, stop + 4, last, 124, 10, 5.25)
            if stop > y + 104:
                raise ValueError((title, stop, y))
            if row == 0:
                sh.line(14, y + 101, 196, y + 101, color=FAINT)
        sh.footer("Ручная сборка   ·   Веер / 250")
        sh.done()
    sh.c.save()


def templates_a3():
    sh = Sheet("veer-250-a3.pdf", "Веер 250 — цельные лекала 1:1 на четырёх листах A3")
    sh.page(420, 297)
    sh.header(
        "G, H, I, J   /   Ручка и усилители",
        "A3   ·   ЛИСТ 01 / 04",
        "Печать 100 %, альбомная ориентация. Сначала измерьте квадрат и линейку. Все лекала комплекта A3 помещаются на листах целиком.",
    )
    piece(sh, "G", (26, 40))
    piece(sh, "I", (207, 39))
    sh.txt(26, 190, "G   /   Арочная ручка · 2 из основной кожи", 10, "Bold")
    sh.txt(
        207, 164, "I   /   Вставка дна · 142 × 116 мм · 1 из уплотнителя", 10, "Bold"
    )
    piece(sh, "H", (192, 190))
    piece(sh, "J", (242, 190))
    for x, info, mat in [
        (205, "H · 26 × 36 мм", "2 из основной кожи"),
        (260, "J · Ø 36 мм", "2 из тонкой кожи"),
    ]:
        sh.txt(x, 236, info, 9, "Bold", align="center")
        sh.txt(x, 243, mat, 8, align="center")
    sh.rect(22, 220, 50, 50, color=INK, width=0.24)
    sh.txt(47, 247, "50 × 50 мм", 10, "Bold", align="center")
    sh.txt(81, 234, "Контроль масштаба", 10, "Bold")
    ruler(sh, 81, 253)
    seam_glyphs(sh, 298, 195)
    sh.footer(
        "Веер 250   ·   выкройка 1:1   ·   припуск по стачным швам 6 мм уже включён"
    )
    sh.done()

    sh.page(420, 297)
    sh.header(
        "A, B, C   /   Панели корпуса",
        "A3   ·   ЛИСТ 02 / 04",
        "A ×2 — перед и спинка. Для B и C выкроите по две обычные и две зеркальные детали. Цифры 1–3 у края обозначают парные вертикальные швы.",
    )
    for key, x in (("A", 15), ("B", 200), ("C", 307)):
        box = parts[key]["bbox"]
        height = box[3] - box[1]
        piece(sh, key, (x, 27 + (253 - height) / 2))
    sh.footer(
        "A   ·   центр корпуса                       B   ·   боковая панель                       C   ·   крыло"
    )
    sh.done()

    sh.page(420, 297)
    sh.header(
        "D   /   Цельное дно",
        "A3   ·   ЛИСТ 03 / 04",
        "1 деталь из основной кожи. Контур повёрнут на 30° и целиком помещается на одном листе. Четыре штрихпунктирные линии отметьте на изнанке.",
    )
    cx, cy = 210, 153
    box = parts["D"]["bbox"]
    width, height = box[2] - box[0], box[3] - box[1]
    sh.c.saveState()
    sh.c.translate(cx * mm, (sh.h - cy) * mm)
    sh.c.rotate(-30)
    sh.c.translate(-cx * mm, -(sh.h - cy) * mm)
    piece(sh, "D", (cx - width / 2, cy - height / 2))
    sh.c.restoreState()
    sh.footer(
        "Каждую кромку дна пришейте к панели с той же буквой. Поперечные короткие метки обозначают середины швов."
    )
    sh.done()

    sh.page(420, 297)
    sh.header(
        "E, F   /   Клапан",
        "A3   ·   ЛИСТ 04 / 04",
        "Вырежьте по одной детали. Узкие концы крепятся к спинке. Широкие закруглённые концы закрывают переднюю панель.",
    )
    piece(sh, "E", (17, 34))
    piece(sh, "F", (213, 31))
    sh.txt(17, 253, "E   /   Лицевая сторона · основная кожа", 11, "Bold")
    sh.wrap(
        17,
        261,
        "Две короткие строки у узкого края совпадают с метками крепления на задней A. Две длинные поперечные линии указывают зоны плавного перегиба.",
        175,
        9,
    )
    sh.txt(213, 253, "F   /   Изнанка клапана · тонкая кожа", 11, "Bold")
    sh.wrap(
        213,
        261,
        "Крест обозначает центр кнопки. После склейки на объёмной форме подрежьте запас 3 мм по краю наружной детали E.",
        178,
        9,
    )
    sh.footer(
        "Размеры в миллиметрах   ·   перед установкой ответной половины кнопки примерьте закрытый клапан на корпусе."
    )
    sh.done()
    sh.c.save()


if __name__ == "__main__":
    DOWNLOAD.mkdir(parents=True, exist_ok=True)
    templates()
    templates_a3()
    guide()
