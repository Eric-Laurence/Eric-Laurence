import json
import math
import os
import random
import urllib.request
from pathlib import Path

LOGIN = os.environ.get("SKYLINE_LOGIN", "Eric-Laurence")
REPO = Path(__file__).resolve().parents[2]
OUTPUT = REPO / "images" / "skyline.svg"

WIDTH, HEIGHT = 1000, 400
HORIZON = 150
FOCAL = 216
EYE = 12.8
NEAREST_ROW = 12.0
LOT = 0.72
TALLEST = 10.2
STOREY = 0.62
BEACONS = 6

TOWER = [
    (0.0, (43, 11, 87)),
    (0.35, (106, 31, 176)),
    (0.65, (214, 58, 184)),
    (0.88, (255, 110, 199)),
    (1.0, (127, 231, 255)),
]
HAZE = (122, 40, 120)
WINDOW_COLORS = ["#ffd88a"] * 6 + ["#8af3ff"] * 3 + ["#ff9be3"] * 2
SUN_STRIPES = [(62, 0.5), (52, 2), (42, 3), (33, 4), (24, 5), (15, 6), (6, 7), (-3, 8)]
CLOUDS = [(500, 96, 150, 1.6), (472, 116, 190, 1.4), (540, 76, 115, 1.3), (190, 60, 110, 1.6), (820, 50, 120, 1.6)]

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { contributionCount weekday } }
      }
    }
  }
}
"""

STYLE = """
.t { transform-box: fill-box; transform-origin: 50% 100%; animation: rise 1.1s cubic-bezier(.2,.8,.2,1) both; }
@keyframes rise { from { transform: scaleY(0.001); } to { transform: scaleY(1); } }
.twinkle { animation: twinkle 3s ease-in-out infinite; }
@keyframes twinkle { 50% { opacity: 0.08; } }
.beacon { fill: #ff4040; animation: blink 2.4s infinite; }
@keyframes blink { 0%, 55%, 90%, 100% { opacity: 0.15; } 60%, 85% { opacity: 1; } }
.flicker { animation: flicker 7s steps(1) infinite; }
@keyframes flicker { 0%, 100% { opacity: 1; } 40% { opacity: 0.1; } 47% { opacity: 1; } 49% { opacity: 0.1; } 52% { opacity: 1; } }
.meteor { animation: meteor 9s linear infinite; }
@keyframes meteor { 0% { transform: translate(0, 0); opacity: 0; } 2% { opacity: 1; } 9% { transform: translate(260px, 52px); opacity: 0; } 100% { transform: translate(260px, 52px); opacity: 0; } }
@media (prefers-reduced-motion: reduce) { .t, .twinkle, .beacon, .flicker, .meteor { animation: none; } .meteor { opacity: 0; } }
"""

DEFS = f"""
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#0b0320"/><stop offset="0.55" stop-color="#2a0b4f"/>
<stop offset="0.85" stop-color="#7a1d72"/><stop offset="1" stop-color="#ff5fa2"/>
</linearGradient>
<linearGradient id="sun" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#ffe259"/><stop offset="0.5" stop-color="#ff9a3d"/><stop offset="1" stop-color="#ff2e88"/>
</linearGradient>
<linearGradient id="ground" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#2a0838"/><stop offset="1" stop-color="#0b0218"/>
</linearGradient>
<linearGradient id="tail" x1="0" y1="0" x2="1" y2="0">
<stop offset="0" stop-color="#fff3fb" stop-opacity="0"/><stop offset="1" stop-color="#fff3fb"/>
</linearGradient>
<linearGradient id="rock" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#3a0d5c"/><stop offset="1" stop-color="#14041f"/>
</linearGradient>
<clipPath id="below"><rect y="{HORIZON}" width="{WIDTH}" height="{HEIGHT - HORIZON}"/></clipPath>
<radialGradient id="pool" cx="0.5" cy="0.5" r="0.5">
<stop offset="0" stop-color="#ff5fb8" stop-opacity="0.45"/><stop offset="1" stop-color="#ff5fb8" stop-opacity="0"/>
</radialGradient>
<radialGradient id="vignette" cx="0.5" cy="0.45" r="0.75">
<stop offset="0.3" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="0.5"/>
</radialGradient>
<filter id="haze" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="14"/></filter>
<filter id="soft" x="-20%" y="-200%" width="140%" height="500%"><feGaussianBlur stdDeviation="2.2"/></filter>
<filter id="bloom" x="-5%" y="-20%" width="110%" height="140%">
<feGaussianBlur stdDeviation="2.2" result="glow"/>
<feMerge><feMergeNode in="glow"/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
"""


def fetch_calendar(login, token):
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "User-Agent": "skyline"},
    )
    with urllib.request.urlopen(request) as response:
        return json.load(response)["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def project(x, y, z):
    return WIDTH / 2 + FOCAL * x / z, HORIZON + FOCAL * (EYE - y) / z


def points(corners):
    return " ".join(f"{sx:.1f},{sy:.1f}" for sx, sy in (project(*c) for c in corners))


def mix(t):
    for (t0, c0), (t1, c1) in zip(TOWER, TOWER[1:]):
        if t <= t1:
            u = (t - t0) / (t1 - t0)
            return tuple(a + (b - a) * u for a, b in zip(c0, c1))
    return TOWER[-1][1]


def fade(rgb, amount):
    return tuple(c + (h - c) * amount for c, h in zip(rgb, HAZE))


def shade(rgb, factor):
    return "#" + "".join(f"{min(255, round(c * factor)):02x}" for c in rgb)


def windows(x0, z, height, distance, rng):
    lit = []
    floor = 0.35
    while floor + 0.3 < height:
        for offset in (0.1, 0.42):
            if rng.random() < 0.4:
                (ax, ay), (bx, by) = project(x0 + offset, floor + 0.28, z), project(x0 + offset + 0.2, floor, z)
                opacity = (1 - distance * 0.5) * rng.uniform(0.6, 1)
                flicker = f' class="flicker" style="animation-delay:{rng.uniform(0, 7):.1f}s"' if rng.random() < 0.04 else ""
                lit.append(
                    f'<rect x="{ax:.1f}" y="{ay:.1f}" width="{bx - ax:.1f}" height="{by - ay:.1f}" '
                    f'fill="{rng.choice(WINDOW_COLORS)}" opacity="{opacity:.2f}"{flicker}/>'
                )
        floor += STOREY
    return "".join(lit)


def tower(week, weekday, count, peak, week_count, beacon):
    x0 = week - week_count / 2
    x1 = x0 + LOT
    z0 = NEAREST_ROW + (6 - weekday)
    z1 = z0 + LOT
    distance = (6 - weekday) / 6
    level = math.sqrt(count / peak)
    height = TALLEST * level
    color = fade(mix(level**0.8), distance * 0.45)

    parts = []
    side_x = x1 if x1 < 0 else x0 if x0 > 0 else None
    if side_x is not None:
        side = [(side_x, 0, z0), (side_x, 0, z1), (side_x, height, z1), (side_x, height, z0)]
        parts.append(f'<polygon points="{points(side)}" fill="{shade(color, 0.5)}"/>')
    front = [(x0, 0, z0), (x1, 0, z0), (x1, height, z0), (x0, height, z0)]
    roof = [(x0, height, z0), (x1, height, z0), (x1, height, z1), (x0, height, z1)]
    parts.append(f'<polygon points="{points(front)}" fill="{shade(color, 0.85)}"/>')
    if side_x is not None:
        (ax, ay), (bx, by) = project(side_x, 0, z0), project(side_x, height, z0)
        parts.append(
            f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" '
            f'stroke="{shade(color, 1.7)}" stroke-width="0.6" opacity="0.8"/>'
        )
    parts.append(windows(x0, z0, height, distance, random.Random(week * 7 + weekday)))
    parts.append(
        f'<polygon points="{points(roof)}" fill="{shade(color, 1.35)}" '
        f'stroke="{shade(color, 1.8)}" stroke-width="0.7"/>'
    )
    if beacon is not None:
        cx, cy = project(x0 + LOT / 2, height, z0 + LOT / 2)
        parts.append(
            f'<circle class="beacon" cx="{cx:.1f}" cy="{cy - 1.8:.1f}" r="1.7" '
            f'style="animation-delay:{beacon * 0.41:.2f}s"/>'
        )
    delay = 0.2 + week * 0.02 + (6 - weekday) * 0.03
    return f'<g class="t" style="animation-delay:{delay:.2f}s">{"".join(parts)}</g>'


def city(weeks):
    lots = [
        (week_index, day["weekday"], day["contributionCount"])
        for week_index, week in enumerate(weeks)
        for day in week["contributionDays"]
        if day["contributionCount"] > 0
    ]
    peak = max(count for _, _, count in lots)
    tallest = sorted(lots, key=lambda lot: -lot[2])[:BEACONS]
    beacons = {(w, d): rank for rank, (w, d, _) in enumerate(tallest)}
    centre = len(weeks) / 2
    lots.sort(key=lambda lot: (lot[1], -abs(lot[0] + LOT / 2 - centre)))
    return "".join(tower(w, d, c, peak, len(weeks), beacons.get((w, d))) for w, d, c in lots)


def grid():
    nearest = FOCAL * EYE / (HEIGHT - HORIZON)
    lines = []
    for x in range(-80, 81, 2):
        (ax, ay), (bx, by) = project(x, 0, nearest), project(x, 0, 400)
        lines.append(f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}"/>')
    for step in (0.4, 1.3, 2.6, 4.4, 7, 10.5, 16, 25, 40, 70, 130):
        _, y = project(0, 0, nearest + step)
        lines.append(f'<line x1="0" y1="{y:.1f}" x2="{WIDTH}" y2="{y:.1f}"/>')
    return "".join(lines)


def stars():
    rng = random.Random(7)
    lights = []
    for index in range(80):
        twinkle = (
            f' class="twinkle" style="animation-duration:{rng.uniform(2, 5):.1f}s;'
            f'animation-delay:{rng.uniform(0, 4):.1f}s"'
            if index % 3 == 0
            else ""
        )
        lights.append(
            f'<circle cx="{rng.uniform(0, WIDTH):.0f}" cy="{rng.uniform(4, HORIZON - 30):.0f}" '
            f'r="{rng.uniform(0.5, 1.4):.1f}" opacity="{rng.uniform(0.25, 0.85):.2f}"{twinkle}/>'
        )
    return "".join(lights)


def sun_stripes():
    stripes = []
    for (top_a, gap_a), (top_b, gap_b) in zip(SUN_STRIPES, SUN_STRIPES[1:]):
        stripes.append(
            f'<rect x="0" y="{HORIZON - top_a}" width="{WIDTH}" height="{gap_a}" fill="black">'
            f'<animate attributeName="y" values="{HORIZON - top_a};{HORIZON - top_b}" dur="5s" repeatCount="indefinite"/>'
            f'<animate attributeName="height" values="{gap_a};{gap_b}" dur="5s" repeatCount="indefinite"/>'
            "</rect>"
        )
    return "".join(stripes)


def clouds():
    return "".join(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}"/>' for x, y, rx, ry in CLOUDS)


def ridge(x_from, x_to, rising, seed, peak):
    rng = random.Random(seed)
    waves = [(frequency, rng.uniform(0, math.tau)) for frequency in (1.0, 2.3, 5.1, 9.7, 17.3)]
    crest = []
    for step in range(81):
        t = step / 80
        envelope = (t if rising else 1 - t) ** 0.7
        roughness = sum(math.sin(t * f * math.tau + phase) / f for f, phase in waves)
        crest.append((x_from + (x_to - x_from) * t, HORIZON - envelope * peak * (0.6 + 0.3 * roughness)))
    outline = " ".join(f"{x:.1f},{y:.1f}" for x, y in crest)
    return (
        f'<polygon points="{x_from},{HORIZON} {outline} {x_to},{HORIZON}" fill="url(#rock)"/>'
        f'<polyline points="{outline}" fill="none" stroke="#ff6ad5" stroke-width="1.3" filter="url(#bloom)"/>'
    )


def svg(calendar):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" role="img" aria-label="A year of GitHub contributions as a city at sunset, one building per day">
<style>{STYLE}</style>
<defs>{DEFS}<mask id="stripes"><rect width="{WIDTH}" height="{HEIGHT}" fill="white"/>{sun_stripes()}</mask></defs>
<rect width="{WIDTH}" height="{HORIZON}" fill="url(#sky)"/>
<g fill="#fff3fb">{stars()}</g>
<line class="meteor" x1="120" y1="28" x2="190" y2="42" stroke="url(#tail)" stroke-width="1.4" stroke-linecap="round"/>
<circle cx="{WIDTH / 2}" cy="{HORIZON - 4}" r="118" fill="#ff2e88" opacity="0.5" filter="url(#haze)"/>
<circle cx="{WIDTH / 2}" cy="{HORIZON - 4}" r="96" fill="url(#sun)" mask="url(#stripes)"/>
<g fill="#ff8fd0" opacity="0.4" filter="url(#soft)">{clouds()}</g>
{ridge(0, 430, False, 3, 58)}
{ridge(570, WIDTH, True, 11, 50)}
<rect y="{HORIZON}" width="{WIDTH}" height="{HEIGHT - HORIZON}" fill="url(#ground)"/>
<ellipse cx="{WIDTH / 2}" cy="{HORIZON}" rx="420" ry="90" fill="url(#pool)" clip-path="url(#below)"/>
<g stroke="#ff3ec9" stroke-opacity="0.32" stroke-width="1" filter="url(#bloom)">{grid()}</g>
<rect y="{HORIZON - 3}" width="{WIDTH}" height="6" fill="#ff7ad0" opacity="0.6" filter="url(#soft)"/>
<rect y="{HORIZON - 1}" width="{WIDTH}" height="2" fill="#ffd6f1"/>
<g filter="url(#bloom)">{city(calendar["weeks"])}</g>
<rect width="{WIDTH}" height="{HEIGHT}" fill="url(#vignette)"/>
</svg>
"""


if __name__ == "__main__":
    calendar = fetch_calendar(LOGIN, os.environ["GITHUB_TOKEN"])
    with open(OUTPUT, "w") as out:
        out.write(svg(calendar))
