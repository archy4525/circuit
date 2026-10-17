"""把題庫裡的結構描述畫成可縮放的電路示意，不使用教材圖片。"""

from __future__ import annotations

from html import escape
from typing import Any

_FONT = "ui-sans-serif, 'Segoe UI', 'PingFang TC', 'Microsoft JhengHei', sans-serif"


def diagram_document(spec: dict[str, Any]) -> tuple[str, int]:
    svg, height = render_svg(spec)
    page = f"""<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>html,body{{margin:0;padding:0;background:transparent;}}</style></head>
<body>{svg}</body></html>"""
    return page, height


def render_svg(spec: dict[str, Any]) -> tuple[str, int]:
    kind = spec.get("kind")
    drawers = {
        "series": _series,
        "divider": _divider,
        "parallel": _parallel,
        "series_parallel": _series_parallel,
        "nested": _nested,
        "node": _node,
        "rc": _rc,
        "rl": _rl,
        "impedance": _impedance,
        "opamp": _opamp,
        "diode": _diode_loop,
        "zener": _zener,
        "bjt": _bjt,
        "thevenin": _thevenin,
    }
    drawer = drawers.get(kind)
    if drawer is None:
        return _frame(spec.get("title") or "電路", "<text x='20' y='80'>沒有可繪製的圖</text>", 120)
    return drawer(spec)


def _frame(title: str, body: str, height: int, caption: str = "") -> tuple[str, int]:
    cap = ""
    if caption:
        cap = (
            f"<text x='200' y='{height - 16}' text-anchor='middle' class='cap'>"
            f"{escape(caption)}</text>"
        )
        height += 8
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 {height}" width="400" role="img" aria-label="{escape(title)}" style="max-width:100%;height:auto;display:block;margin:0 auto">
<style>
  .wire {{ fill: none; stroke: #243026; stroke-width: 2.4; stroke-linecap: round; stroke-linejoin: round; }}
  .fill {{ fill: #e7f3ee; stroke: #243026; stroke-width: 2.2; }}
  .ink {{ font-family: {_FONT}; font-size: 15px; font-weight: 700; fill: #1c1915; }}
  .lab {{ font-family: {_FONT}; font-size: 14px; font-weight: 650; fill: #1c1915; }}
  .cap {{ font-family: {_FONT}; font-size: 13px; fill: #5c564c; }}
  .mark {{ font-family: {_FONT}; font-size: 13px; font-weight: 700; fill: #0f6e56; }}
</style>
<rect x="1" y="1" width="398" height="{height - 2}" rx="16" fill="#fffdf8" stroke="#e4dccb"/>
<text x="18" y="28" class="ink">{escape(title)}</text>
{body}
{cap}
</svg>"""
    return svg, height


def _polyline(points: list[tuple[float, float]], cls: str = "wire") -> str:
    coords = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f'<polyline class="{cls}" points="{coords}"/>'


def _text(x: float, y: float, value: str, cls: str = "lab", anchor: str = "middle") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" class="{cls}">'
        f"{escape(value)}</text>"
    )


def _dot(x: float, y: float) -> str:
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="#243026"/>'


def _resistor(x1: float, x2: float, y: float) -> str:
    lead = 10
    body = max(8, x2 - x1 - 2 * lead)
    n = 6
    step = body / n
    points = [(x1, y), (x1 + lead, y)]
    for index in range(n):
        px = x1 + lead + step * (index + 0.5)
        py = y - 8 if index % 2 == 0 else y + 8
        points.append((px, py))
    points.extend([(x2 - lead, y), (x2, y)])
    return _polyline(points)


def _source(cx: float, cy: float) -> str:
    return f'<circle class="fill" cx="{cx:.1f}" cy="{cy:.1f}" r="16"/>'


def _capacitor(cx: float, y: float) -> str:
    return (
        f'<line class="wire" x1="{cx - 18}" y1="{y}" x2="{cx - 5}" y2="{y}"/>'
        f'<line class="wire" x1="{cx - 5}" y1="{y - 14}" x2="{cx - 5}" y2="{y + 14}"/>'
        f'<line class="wire" x1="{cx + 5}" y1="{y - 14}" x2="{cx + 5}" y2="{y + 14}"/>'
        f'<line class="wire" x1="{cx + 5}" y1="{y}" x2="{cx + 18}" y2="{y}"/>'
    )


def _inductor(x1: float, x2: float, y: float) -> str:
    mid = (x1 + x2) / 2
    return (
        f'<path class="wire" d="M {x1:.1f} {y:.1f} '
        f'Q {mid - 24:.1f} {y - 16:.1f} {mid - 12:.1f} {y:.1f} '
        f'Q {mid:.1f} {y - 16:.1f} {mid + 12:.1f} {y:.1f} '
        f'Q {mid + 24:.1f} {y - 16:.1f} {x2:.1f} {y:.1f}"/>'
    )


def _diode(cx: float, y: float) -> str:
    return (
        f'<polygon points="{cx - 12},{y - 12} {cx + 10},{y} {cx - 12},{y + 12}" fill="#fffdf8" stroke="#243026" stroke-width="2.2"/>'
        f'<line class="wire" x1="{cx + 10}" y1="{y - 13}" x2="{cx + 10}" y2="{y + 13}"/>'
    )


def _ground(x: float, y: float) -> str:
    return (
        f'<line class="wire" x1="{x}" y1="{y}" x2="{x}" y2="{y + 12}"/>'
        f'<line class="wire" x1="{x - 12}" y1="{y + 12}" x2="{x + 12}" y2="{y + 12}"/>'
        f'<line class="wire" x1="{x - 8}" y1="{y + 17}" x2="{x + 8}" y2="{y + 17}"/>'
        f'<line class="wire" x1="{x - 4}" y1="{y + 22}" x2="{x + 4}" y2="{y + 22}"/>'
    )


def _v_res_loop(parts: list[dict[str, str]], y: float) -> str:
    chunks: list[str] = []
    margin = 36
    usable = 400 - 2 * margin
    count = max(1, len(parts))
    slot = usable / count
    for index, part in enumerate(parts):
        center = margin + slot * (index + 0.5)
        left = center - min(34, slot / 2 - 4)
        right = center + min(34, slot / 2 - 4)
        symbol = part.get("sym", "r")
        if symbol == "v":
            chunks.append(_source(center, y))
            chunks.append(_text(center, y + 5, "+", "mark"))
        elif symbol == "c":
            chunks.append(_capacitor(center, y))
        elif symbol == "l":
            chunks.append(_inductor(left, right, y))
        elif symbol == "d":
            chunks.append(_diode(center, y))
        elif symbol == "x":
            chunks.append(
                f'<rect class="fill" x="{center - 28}" y="{y - 16}" width="56" height="32" rx="6"/>'
            )
        else:
            chunks.append(_resistor(left, right, y))
        chunks.append(_text(center, y - 24, part.get("name", "")))
    return "".join(chunks)


def _series(spec: dict[str, Any]) -> tuple[str, int]:
    parts = spec.get("parts") or []
    y = 108
    body = (
        f'<line class="wire" x1="28" y1="{y}" x2="372" y2="{y}"/>'
        f'<line class="wire" x1="28" y1="{y}" x2="28" y2="168"/>'
        f'<line class="wire" x1="372" y1="{y}" x2="372" y2="168"/>'
        f'<line class="wire" x1="28" y1="168" x2="372" y2="168"/>'
        + _v_res_loop(parts, y)
    )
    return _frame(spec.get("title") or "串聯迴路", body, 206, spec.get("caption", ""))


def _divider(spec: dict[str, Any]) -> tuple[str, int]:
    return _frame(
        spec.get("title") or "分壓電路",
        _vertical_divider(spec),
        230,
        spec.get("caption", ""),
    )


def _vertical_resistor(x: float, y1: float, y2: float) -> str:
    lead = 8
    body = max(8, y2 - y1 - 2 * lead)
    n = 6
    step = body / n
    points = [(x, y1), (x, y1 + lead)]
    for index in range(n):
        py = y1 + lead + step * (index + 0.5)
        px = x - 8 if index % 2 == 0 else x + 8
        points.append((px, py))
    points.extend([(x, y2 - lead), (x, y2)])
    return _polyline(points)


def _vertical_divider(spec: dict[str, Any]) -> str:
    return "".join(
        [
            '<line class="wire" x1="78" y1="64" x2="230" y2="64"/>',
            '<line class="wire" x1="78" y1="176" x2="250" y2="176"/>',
            '<line class="wire" x1="230" y1="64" x2="230" y2="78"/>',
            '<line class="wire" x1="230" y1="162" x2="230" y2="176"/>',
            _source(78, 120),
            _text(78, 125, "+", "mark"),
            _text(78, 112, "−", "lab"),
            _text(78, 52, spec.get("vin", "")),
            _vertical_resistor(230, 78, 112),
            _text(268, 100, spec.get("r_top", ""), "lab", "start"),
            _dot(230, 120),
            _vertical_resistor(230, 128, 162),
            _text(268, 150, spec.get("r_bot", ""), "lab", "start"),
            '<line class="wire" x1="230" y1="120" x2="320" y2="120"/>',
            _text(348, 116, spec.get("meter", "V"), "mark", "end"),
            '<circle class="fill" cx="332" cy="120" r="14"/>',
            _text(332, 125, "V", "mark"),
        ]
    )


def _parallel(spec: dict[str, Any]) -> tuple[str, int]:
    branches = spec.get("branches") or ["", ""]
    body = "".join(
        [
            '<line class="wire" x1="90" y1="78" x2="300" y2="78"/>',
            '<line class="wire" x1="90" y1="168" x2="300" y2="168"/>',
            '<line class="wire" x1="150" y1="78" x2="150" y2="96"/>',
            '<line class="wire" x1="150" y1="150" x2="150" y2="168"/>',
            '<line class="wire" x1="250" y1="78" x2="250" y2="96"/>',
            '<line class="wire" x1="250" y1="150" x2="250" y2="168"/>',
            _vertical_resistor(150, 96, 150),
            _vertical_resistor(250, 96, 150),
            _dot(150, 78),
            _dot(250, 78),
            _text(150, 92, branches[0] if branches else ""),
            _text(250, 92, branches[1] if len(branches) > 1 else ""),
            _text(48, 74, spec.get("feed", ""), "mark", "start"),
            '<line class="wire" x1="70" y1="78" x2="90" y2="78"/>',
            '<polygon points="86,74 98,78 86,82" fill="#0f6e56"/>',
        ]
    )
    return _frame(spec.get("title") or "並聯支路", body, 214, spec.get("caption", ""))


def _series_parallel(spec: dict[str, Any]) -> tuple[str, int]:
    branches = spec.get("branches") or ["", ""]
    body = "".join(
        [
            '<line class="wire" x1="40" y1="92" x2="150" y2="92"/>',
            '<line class="wire" x1="40" y1="92" x2="40" y2="176"/>',
            '<line class="wire" x1="40" y1="176" x2="320" y2="176"/>',
            '<line class="wire" x1="210" y1="92" x2="320" y2="92"/>',
            '<line class="wire" x1="320" y1="92" x2="320" y2="176"/>',
            _resistor(78, 150, 92),
            _text(114, 74, spec.get("series", "")),
            '<line class="wire" x1="210" y1="92" x2="210" y2="108"/>',
            '<line class="wire" x1="280" y1="92" x2="280" y2="108"/>',
            '<line class="wire" x1="210" y1="158" x2="210" y2="176"/>',
            '<line class="wire" x1="280" y1="158" x2="280" y2="176"/>',
            _vertical_resistor(210, 108, 158),
            _vertical_resistor(280, 108, 158),
            _dot(210, 92),
            _dot(280, 92),
            _text(188, 140, branches[0], "lab", "end"),
            _text(302, 140, branches[1] if len(branches) > 1 else "", "lab", "start"),
            _source(40, 134),
            _text(40, 139, "+", "mark"),
        ]
    )
    return _frame(spec.get("title") or "串並聯", body, 214, spec.get("caption", ""))


def _nested(spec: dict[str, Any]) -> tuple[str, int]:
    right = spec.get("right_series") or ["", ""]
    body = "".join(
        [
            '<line class="wire" x1="36" y1="78" x2="150" y2="78"/>',
            '<line class="wire" x1="36" y1="78" x2="36" y2="188"/>',
            '<line class="wire" x1="36" y1="188" x2="330" y2="188"/>',
            '<line class="wire" x1="190" y1="78" x2="330" y2="78"/>',
            '<line class="wire" x1="330" y1="78" x2="330" y2="188"/>',
            _resistor(70, 146, 78),
            _text(108, 62, spec.get("series", "")),
            '<line class="wire" x1="190" y1="78" x2="190" y2="98"/>',
            '<line class="wire" x1="270" y1="78" x2="270" y2="96"/>',
            '<line class="wire" x1="190" y1="168" x2="190" y2="188"/>',
            '<line class="wire" x1="270" y1="168" x2="270" y2="188"/>',
            _vertical_resistor(190, 98, 168),
            _text(168, 138, spec.get("left", ""), "lab", "end"),
            _resistor(246, 294, 116),
            _text(308, 112, right[0], "lab", "start"),
            _resistor(246, 294, 150),
            _text(308, 146, right[1] if len(right) > 1 else "", "lab", "start"),
            '<line class="wire" x1="270" y1="96" x2="270" y2="104"/>',
            '<line class="wire" x1="270" y1="128" x2="270" y2="138"/>',
            '<line class="wire" x1="270" y1="162" x2="270" y2="168"/>',
            _dot(190, 78),
            _dot(270, 78),
            _source(36, 133),
            _text(36, 138, "+", "mark"),
        ]
    )
    return _frame(spec.get("title") or "串並聯", body, 226, spec.get("caption", ""))


def _node(spec: dict[str, Any]) -> tuple[str, int]:
    ins = spec.get("ins") or []
    outs = spec.get("outs") or []
    body = ['<circle class="fill" cx="200" cy="112" r="22"/>', _text(200, 117, "節點", "mark")]
    flat = [("入 " + item) for item in ins] + [("出 " + item) for item in outs]
    anchors = [(120, 70), (200, 48), (280, 70), (120, 168), (280, 168)]
    for label, (x, y) in zip(flat, anchors):
        body.append(_text(x, y, label))
        body.append(f'<line class="wire" x1="{x}" y1="{y + 6}" x2="200" y2="112"/>')
    return _frame(spec.get("title") or "節點電流", "".join(body), 214, spec.get("caption", ""))


def _rc(spec: dict[str, Any]) -> tuple[str, int]:
    body = "".join(
        [
            '<line class="wire" x1="40" y1="96" x2="360" y2="96"/>',
            '<line class="wire" x1="40" y1="96" x2="40" y2="168"/>',
            '<line class="wire" x1="360" y1="96" x2="360" y2="168"/>',
            '<line class="wire" x1="40" y1="168" x2="360" y2="168"/>',
            _source(70, 96),
            _text(70, 78, spec.get("v", "")),
            '<line class="wire" x1="150" y1="84" x2="168" y2="108"/>',
            _text(150, 78, "t=0"),
            _resistor(210, 280, 96),
            _text(245, 78, spec.get("r", "")),
            _capacitor(330, 96),
            _text(330, 78, spec.get("c", "")),
        ]
    )
    return _frame(spec.get("title") or "RC 暫態", body, 206, spec.get("caption", ""))


def _rl(spec: dict[str, Any]) -> tuple[str, int]:
    body = "".join(
        [
            '<line class="wire" x1="40" y1="100" x2="360" y2="100"/>',
            '<line class="wire" x1="40" y1="100" x2="40" y2="168"/>',
            '<line class="wire" x1="360" y1="100" x2="360" y2="168"/>',
            '<line class="wire" x1="40" y1="168" x2="360" y2="168"/>',
            _source(78, 100),
            _text(78, 80, spec.get("v", "")),
            _resistor(160, 230, 100),
            _text(195, 80, spec.get("r", "")),
            _inductor(270, 340, 100),
            _text(305, 78, spec.get("l", "")),
        ]
    )
    return _frame(spec.get("title") or "RL 暫態", body, 206, spec.get("caption", ""))


def _impedance(spec: dict[str, Any]) -> tuple[str, int]:
    parts = [{"sym": "v", "name": spec.get("v", "")}]
    for name in spec.get("parts") or []:
        parts.append({"sym": "x", "name": name})
    return _series({**spec, "title": spec.get("title") or "阻抗串聯", "parts": parts})


def _opamp(spec: dict[str, Any]) -> tuple[str, int]:
    mode = spec.get("mode", "inv")
    if mode == "noninv":
        body = _opamp_noninv(spec)
    elif mode == "sum":
        body = _opamp_sum(spec)
    elif mode == "diff":
        body = _opamp_diff(spec)
    else:
        body = _opamp_inv(spec)
    return _frame(spec.get("title") or "運算放大器", body, 236, spec.get("caption", ""))


def _triangle() -> str:
    return (
        '<polygon points="168,58 168,176 292,117" class="fill"/>'
        + _text(186, 96, "−", "mark", "start")
        + _text(186, 150, "+", "mark", "start")
    )


def _opamp_inv(spec: dict[str, Any]) -> str:
    return "".join(
        [
            _triangle(),
            '<line class="wire" x1="36" y1="90" x2="168" y2="90"/>',
            _resistor(70, 140, 90),
            _text(105, 74, spec.get("rin", "")),
            _text(28, 86, spec.get("vin", ""), "lab", "start"),
            '<line class="wire" x1="292" y1="117" x2="360" y2="117"/>',
            _text(360, 108, "出", "mark", "end"),
            '<line class="wire" x1="120" y1="90" x2="120" y2="46"/>',
            '<line class="wire" x1="120" y1="46" x2="330" y2="46"/>',
            '<line class="wire" x1="330" y1="46" x2="330" y2="117"/>',
            _resistor(180, 260, 46),
            _text(220, 36, spec.get("rf", "")),
            '<line class="wire" x1="168" y1="144" x2="130" y2="144"/>',
            _ground(130, 144),
            _dot(120, 90),
        ]
    )


def _opamp_noninv(spec: dict[str, Any]) -> str:
    return "".join(
        [
            _triangle(),
            '<line class="wire" x1="40" y1="144" x2="168" y2="144"/>',
            _text(36, 136, spec.get("vin", ""), "lab", "start"),
            '<line class="wire" x1="292" y1="117" x2="364" y2="117"/>',
            _text(364, 108, "出", "mark", "end"),
            '<line class="wire" x1="168" y1="90" x2="120" y2="90"/>',
            '<line class="wire" x1="120" y1="90" x2="120" y2="168"/>',
            _ground(120, 168),
            _vertical_resistor(120, 100, 140),
            _text(78, 124, spec.get("rg", ""), "lab", "end"),
            '<line class="wire" x1="120" y1="90" x2="120" y2="48"/>',
            '<line class="wire" x1="120" y1="48" x2="330" y2="48"/>',
            '<line class="wire" x1="330" y1="48" x2="330" y2="117"/>',
            _resistor(190, 270, 48),
            _text(230, 38, spec.get("rf", "")),
            _dot(120, 90),
        ]
    )


def _opamp_sum(spec: dict[str, Any]) -> str:
    inputs = spec.get("inputs") or ["", ""]
    return "".join(
        [
            _triangle(),
            '<line class="wire" x1="30" y1="78" x2="168" y2="90"/>',
            '<line class="wire" x1="30" y1="112" x2="168" y2="90"/>',
            _text(24, 74, inputs[0], "lab", "start"),
            _text(24, 128, inputs[1] if len(inputs) > 1 else "", "lab", "start"),
            _text(78, 70, spec.get("rin", "")),
            '<line class="wire" x1="292" y1="117" x2="360" y2="117"/>',
            '<line class="wire" x1="140" y1="90" x2="140" y2="46"/>',
            '<line class="wire" x1="140" y1="46" x2="328" y2="46"/>',
            '<line class="wire" x1="328" y1="46" x2="328" y2="117"/>',
            _resistor(200, 270, 46),
            _text(235, 36, spec.get("rf", "")),
            '<line class="wire" x1="168" y1="150" x2="132" y2="150"/>',
            _ground(132, 150),
            _dot(140, 90),
        ]
    )


def _opamp_diff(spec: dict[str, Any]) -> str:
    return "".join(
        [
            _triangle(),
            '<line class="wire" x1="28" y1="90" x2="168" y2="90"/>',
            _resistor(60, 130, 90),
            _text(24, 78, spec.get("v1", ""), "lab", "start"),
            _text(96, 78, spec.get("rin", "")),
            '<line class="wire" x1="292" y1="117" x2="366" y2="117"/>',
            '<line class="wire" x1="118" y1="90" x2="118" y2="46"/>',
            '<line class="wire" x1="118" y1="46" x2="330" y2="46"/>',
            '<line class="wire" x1="330" y1="46" x2="330" y2="117"/>',
            _resistor(190, 270, 46),
            _text(230, 36, spec.get("rf", "")),
            '<line class="wire" x1="28" y1="150" x2="168" y2="150"/>',
            _resistor(60, 130, 150),
            _text(24, 166, spec.get("v2", ""), "lab", "start"),
            '<line class="wire" x1="118" y1="150" x2="118" y2="196"/>',
            _ground(118, 196),
            _vertical_resistor(118, 160, 190),
            _text(78, 186, spec.get("rg", ""), "lab", "end"),
            _dot(118, 90),
            _dot(118, 150),
        ]
    )


def _diode_loop(spec: dict[str, Any]) -> tuple[str, int]:
    parts = [
        {"sym": "v", "name": spec.get("v", "")},
        {"sym": "d", "name": spec.get("vf", "二極體")},
        {"sym": "r", "name": spec.get("r", "")},
    ]
    return _series({**spec, "title": spec.get("title") or "二極體迴路", "parts": parts})


def _zener(spec: dict[str, Any]) -> tuple[str, int]:
    body = "".join(
        [
            '<line class="wire" x1="48" y1="78" x2="250" y2="78"/>',
            '<line class="wire" x1="48" y1="78" x2="48" y2="176"/>',
            '<line class="wire" x1="48" y1="176" x2="250" y2="176"/>',
            _source(48, 127),
            _text(48, 132, "+", "mark"),
            _text(48, 62, spec.get("v", "")),
            _resistor(120, 200, 78),
            _text(160, 62, spec.get("r", "")),
            '<line class="wire" x1="250" y1="78" x2="250" y2="100"/>',
            '<line class="wire" x1="250" y1="150" x2="250" y2="176"/>',
            _diode(250, 128).replace('points="238,116 260,128 238,140"', 'points="238,140 260,128 238,116"'),
            '<line class="wire" x1="260" y1="115" x2="260" y2="141"/>',
            '<polyline class="wire" points="236,112 246,122 256,112"/>',
            _text(292, 126, spec.get("vz", ""), "lab", "start"),
            _dot(250, 78),
            '<line class="wire" x1="250" y1="78" x2="340" y2="78"/>',
            _text(360, 74, "輸出", "mark", "end"),
        ]
    )
    return _frame(spec.get("title") or "齊納穩壓", body, 214, spec.get("caption", ""))


def _bjt(spec: dict[str, Any]) -> tuple[str, int]:
    body = "".join(
        [
            '<line class="wire" x1="70" y1="52" x2="300" y2="52"/>',
            _text(40, 48, spec.get("vcc", ""), "mark", "start"),
            '<line class="wire" x1="120" y1="52" x2="120" y2="86"/>',
            '<line class="wire" x1="230" y1="52" x2="230" y2="86"/>',
            _vertical_resistor(120, 86, 130),
            _text(78, 112, spec.get("rb", ""), "lab", "end"),
            _vertical_resistor(230, 86, 130),
            _text(252, 112, spec.get("rc", ""), "lab", "start"),
            '<line class="wire" x1="150" y1="148" x2="214" y2="148"/>',
            '<line class="wire" x1="120" y1="148" x2="150" y2="148"/>',
            '<line class="wire" x1="214" y1="130" x2="214" y2="166"/>',
            '<polygon points="214,118 214,178 268,148" class="fill"/>',
            '<line class="wire" x1="248" y1="132" x2="214" y2="148"/>',
            '<line class="wire" x1="248" y1="164" x2="214" y2="148"/>',
            '<polygon points="236,158 248,164 240,148" fill="#243026"/>',
            '<line class="wire" x1="248" y1="164" x2="248" y2="196"/>',
            _ground(248, 196),
            _text(300, 150, spec.get("beta", ""), "lab", "start"),
            _dot(120, 52),
            _dot(230, 52),
        ]
    )
    return _frame(spec.get("title") or "電晶體偏壓", body, 236, spec.get("caption", ""))


def _thevenin(spec: dict[str, Any]) -> tuple[str, int]:
    return _divider(
        {
            "title": spec.get("title") or "開路端口",
            "vin": spec.get("v", ""),
            "r_top": spec.get("r1", ""),
            "r_bot": spec.get("r2", ""),
            "meter": "開路",
            "caption": spec.get("caption", "由下方電阻兩端看進去"),
        }
    )
