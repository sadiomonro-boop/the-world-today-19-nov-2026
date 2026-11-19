#!/usr/bin/env python3
"""The World Today - front-page summary of world news, Thursday 19 November 2026.

Pure Python standard library. Draws a 1024x1024 newspaper front page and
writes entry.png. Deterministic: two runs produce byte-identical output.
No network access at runtime.
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024

PAPER = (244, 238, 222)
PAPER_DARK = (232, 225, 205)
INK = (24, 24, 24)
RED = (172, 28, 28)
NAVY = (28, 54, 92)
NAVY_DARK = (18, 38, 66)
SKY_TOP = (126, 168, 205)
SKY_MID = (186, 205, 226)
SKY_LOW = (238, 214, 160)
SEA_TOP = (38, 92, 128)
SEA_BOT = (16, 52, 84)
SUN = (232, 178, 64)
GOLD = (170, 128, 16)
GREY = (110, 108, 98)
WHITE = (250, 248, 240)

buf = bytearray(W * H * 3)


def set_px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i] = c[0]
        buf[i + 1] = c[1]
        buf[i + 2] = c[2]


def fill_rect(x, y, w, h, c):
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    row = bytes(c) * (x1 - x0)
    for yy in range(y0, y1):
        i = (yy * W + x0) * 3
        buf[i:i + len(row)] = row


def rect_border(x, y, w, h, c, t=1):
    fill_rect(x, y, w, t, c)
    fill_rect(x, y + h - t, w, t, c)
    fill_rect(x, y, t, h, c)
    fill_rect(x + w - t, y, t, h, c)


def hline(x, y, w, c, t=1):
    fill_rect(x, y, w, t, c)


def vline(x, y, h, c, t=1):
    fill_rect(x, y, t, h, c)


def _brush(cx, cy, c, t):
    r = t // 2
    fill_rect(cx - r, cy - r, t, t, c)


def line(x0, y0, x1, y1, c, t=1):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        _brush(x0, y0, c, t)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def filled_circle(cx, cy, r, c):
    r2 = r * r
    for yy in range(-r, r + 1):
        dx = int((r2 - yy * yy) ** 0.5)
        fill_rect(cx - dx, cy + yy, 2 * dx + 1, 1, c)


def circle_outline(cx, cy, r, c, t=1):
    steps = max(24, r * 6)
    prev = None
    for k in range(steps + 1):
        a = 2.0 * math.pi * k / steps
        px = int(round(cx + r * math.cos(a)))
        py = int(round(cy + r * math.sin(a)))
        if prev is not None:
            line(prev[0], prev[1], px, py, c, t)
        prev = (px, py)


# ---------------------------------------------------------------- font
# Stroke font on a 5x7 grid. Each glyph is a list of segments (x1, y1, x2, y2).
GLYPHS = {
    "A": [(0, 6, 2, 0), (2, 0, 4, 6), (1, 4, 3, 4)],
    "B": [(0, 0, 0, 6), (0, 0, 4, 0), (0, 3, 4, 3), (0, 6, 4, 6),
          (4, 0, 4, 3), (4, 3, 4, 6)],
    "C": [(0, 0, 4, 0), (0, 0, 0, 6), (0, 6, 4, 6)],
    "D": [(0, 0, 0, 6), (0, 0, 4, 0), (0, 6, 4, 6), (4, 1, 4, 5)],
    "E": [(0, 0, 0, 6), (0, 0, 4, 0), (0, 3, 3, 3), (0, 6, 4, 6)],
    "F": [(0, 0, 0, 6), (0, 0, 4, 0), (0, 3, 3, 3)],
    "G": [(0, 0, 4, 0), (0, 0, 0, 6), (0, 6, 4, 6), (4, 3, 4, 6),
          (2, 3, 4, 3)],
    "H": [(0, 0, 0, 6), (4, 0, 4, 6), (0, 3, 4, 3)],
    "I": [(0, 0, 4, 0), (2, 0, 2, 6), (0, 6, 4, 6)],
    "J": [(0, 0, 4, 0), (4, 0, 4, 6), (0, 6, 4, 6), (0, 4, 0, 6)],
    "K": [(0, 0, 0, 6), (2, 3, 4, 0), (2, 3, 4, 6)],
    "L": [(0, 0, 0, 6), (0, 6, 4, 6)],
    "M": [(0, 0, 0, 6), (4, 0, 4, 6), (0, 0, 2, 3), (2, 3, 4, 0)],
    "N": [(0, 0, 0, 6), (4, 0, 4, 6), (0, 0, 4, 6)],
    "O": [(0, 0, 4, 0), (0, 6, 4, 6), (0, 0, 0, 6), (4, 0, 4, 6)],
    "P": [(0, 0, 0, 6), (0, 0, 4, 0), (0, 3, 4, 3), (4, 0, 4, 3)],
    "Q": [(0, 0, 4, 0), (0, 6, 4, 6), (0, 0, 0, 6), (4, 0, 4, 6),
          (3, 4, 4, 6)],
    "R": [(0, 0, 0, 6), (0, 0, 4, 0), (0, 3, 4, 3), (4, 0, 4, 3),
          (2, 3, 4, 6)],
    "S": [(0, 0, 4, 0), (0, 0, 0, 3), (0, 3, 4, 3), (4, 3, 4, 6),
          (0, 6, 4, 6)],
    "T": [(0, 0, 4, 0), (2, 0, 2, 6)],
    "U": [(0, 0, 0, 6), (4, 0, 4, 6), (0, 6, 4, 6)],
    "V": [(0, 0, 2, 6), (2, 6, 4, 0)],
    "W": [(0, 0, 1, 6), (1, 6, 2, 3), (2, 3, 3, 6), (3, 6, 4, 0)],
    "X": [(0, 0, 4, 6), (4, 0, 0, 6)],
    "Y": [(0, 0, 2, 3), (4, 0, 2, 3), (2, 3, 2, 6)],
    "Z": [(0, 0, 4, 0), (4, 0, 0, 6), (0, 6, 4, 6)],
    "0": [(0, 0, 4, 0), (0, 6, 4, 6), (0, 0, 0, 6), (4, 0, 4, 6)],
    "1": [(2, 0, 2, 6), (1, 1, 2, 0), (0, 6, 4, 6)],
    "2": [(0, 0, 4, 0), (4, 0, 4, 3), (0, 3, 4, 3), (0, 3, 0, 6),
          (0, 6, 4, 6)],
    "3": [(0, 0, 4, 0), (4, 0, 4, 6), (0, 3, 4, 3), (0, 6, 4, 6)],
    "4": [(0, 0, 0, 3), (0, 3, 4, 3), (4, 0, 4, 6)],
    "5": [(0, 0, 4, 0), (0, 0, 0, 3), (0, 3, 4, 3), (4, 3, 4, 6),
          (0, 6, 4, 6)],
    "6": [(0, 0, 4, 0), (0, 0, 0, 6), (0, 3, 4, 3), (4, 3, 4, 6),
          (0, 6, 4, 6)],
    "7": [(0, 0, 4, 0), (4, 0, 4, 6)],
    "8": [(0, 0, 4, 0), (0, 6, 4, 6), (0, 0, 0, 6), (4, 0, 4, 6),
          (0, 3, 4, 3)],
    "9": [(0, 0, 4, 0), (0, 0, 0, 3), (4, 0, 4, 6), (0, 3, 4, 3),
          (0, 6, 4, 6)],
    ".": [(2, 6, 2, 6)],
    ",": [(2, 5, 2, 6), (1, 6, 2, 5)],
    ":": [(2, 1, 2, 1), (2, 5, 2, 5)],
    ";": [(2, 1, 2, 1), (2, 4, 2, 5), (1, 6, 2, 5)],
    "!": [(2, 0, 2, 4), (2, 6, 2, 6)],
    "?": [(0, 0, 4, 0), (4, 0, 4, 2), (2, 2, 4, 2), (2, 3, 2, 4),
          (2, 6, 2, 6)],
    "-": [(0, 3, 4, 3)],
    "/": [(4, 0, 0, 6)],
    "(": [(3, 0, 1, 2), (1, 2, 1, 4), (1, 4, 3, 6)],
    ")": [(1, 0, 3, 2), (3, 2, 3, 4), (3, 4, 1, 6)],
    '"': [(1, 0, 1, 1), (3, 0, 3, 1)],
    "'": [(2, 0, 2, 1)],
    "%": [(0, 0, 0, 1), (4, 5, 4, 6), (4, 0, 0, 6)],
    "$": [(2, 0, 2, 6), (0, 1, 4, 1), (0, 3, 4, 3), (0, 5, 4, 5)],
    "+": [(2, 0, 2, 6), (0, 3, 4, 3)],
    "=": [(0, 2, 4, 2), (0, 4, 4, 4)],
    "#": [(1, 0, 1, 6), (3, 0, 3, 6), (0, 2, 4, 2), (0, 4, 4, 4)],
    "*": [(2, 0, 2, 6), (0, 2, 4, 4), (4, 2, 0, 4)],
    "<": [(4, 0, 0, 3), (0, 3, 4, 6)],
    ">": [(0, 0, 4, 3), (4, 3, 0, 6)],
    "[": [(0, 0, 3, 0), (0, 0, 0, 6), (0, 6, 3, 6)],
    "]": [(1, 0, 4, 0), (4, 0, 4, 6), (1, 6, 4, 6)],
    "_": [(0, 6, 4, 6)],
}

ADV = 6  # glyph advance in grid units (5 + 1 space)


def _seg_line(x0, y0, x1, y1, c, t):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        _brush(x0, y0, c, t)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def draw_char(ch, x, y, scale, thick, c):
    segs = GLYPHS.get(ch)
    if not segs:
        return
    for (x1, y1, x2, y2) in segs:
        _seg_line(x + x1 * scale, y + y1 * scale,
                  x + x2 * scale, y + y2 * scale, c, thick)


def text_w(s, scale):
    return len(s) * ADV * scale - scale


def draw_text(s, x, y, scale, thick, c):
    cx = x
    for ch in s:
        draw_char(ch, cx, y, scale, thick, c)
        cx += ADV * scale
    return cx - x - scale if s else 0


def draw_text_centered(s, cx, y, scale, thick, c):
    w = text_w(s, scale)
    draw_text(s, cx - w // 2, y, scale, thick, c)
    return w


# ---------------------------------------------------------------- text wrap
def wrap_lines(text, scale, first_w, rest_w):
    """Greedy word wrap. First line gets first_w px, later lines rest_w px.
    Returns a list of lines."""
    words = text.split(" ")
    lines = []
    cur = ""
    limit = first_w
    for wd in words:
        trial = wd if not cur else cur + " " + wd
        if text_w(trial, scale) <= limit or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
            limit = rest_w
    if cur:
        lines.append(cur)
    return lines


def draw_wrapped(text, x, y, scale, thick, c, first_w, rest_w, max_lines,
                 line_h, first_color=None, first_prefix=None):
    """Draw wrapped text; if first_prefix is given, it is drawn in
    first_color at the start of line 1 and the first line is shortened."""
    if first_prefix:
        pw = text_w(first_prefix, scale)
        lines = wrap_lines(text, scale, first_w - pw - 3 * scale, rest_w)
    else:
        lines = wrap_lines(text, scale, first_w, rest_w)
    lines = lines[:max_lines]
    cy = y
    for i, ln in enumerate(lines):
        if i == 0 and first_prefix:
            draw_text(first_prefix, x, cy, scale, thick, first_color)
            draw_text(ln, x + text_w(first_prefix, scale) + 3 * scale,
                      cy, scale, thick, c)
        else:
            draw_text(ln, x, cy, scale, thick, c)
        cy += line_h
    return cy


# ---------------------------------------------------------------- grain
def grain(amount=3, seed=20261119):
    """Deterministic paper grain over the whole image (LCG)."""
    state = seed & 0x7FFFFFFF
    n = W * H * 3
    i = 0
    while i < n:
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        d = ((state >> 16) % (2 * amount + 1)) - amount
        v = buf[i] + d
        buf[i] = 0 if v < 0 else (255 if v > 255 else v)
        i += 1


# ---------------------------------------------------------------- PNG encode
def _chunk(tag, data):
    out = struct.pack(">I", len(data)) + tag + data
    out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return out


def png_bytes():
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw += buf[y * W * 3:(y + 1) * W * 3]
    comp = zlib.compress(bytes(raw), 9)
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", comp)
    png += _chunk(b"IEND", b"")
    return png


# ---------------------------------------------------------------- news data
# Stories are the 19 November 2026 news cycle as reported that day; most
# broke late on 18 Nov UTC or in the Asian morning of 19 Nov. Verified
# against live news search on 19 Nov 2026; claims the red team flagged
# as stale or overstated were fixed or swapped out.
HERO = {
    "kicker": "TOP STORY - MIDDLE EAST",
    "headline": "US AND IRAN TRADE FIRE AS GULF CRISIS WIDENS",
    "standfirst": ("US STRIKES HIT A MISSILE SITE ON QESHM ISLAND AFTER IRAN "
                   "ATTACKED A US RADAR POST IN BAHRAIN. IRAN CLAIMS A STRIKE "
                   "ON A US BASE IN KUWAIT, AND SHIPS IN THE STRAIT OF "
                   "HORMUZ WERE ATTACKED. WASHINGTON HAS NOW SENT A THIRD "
                   "CARRIER TO THE REGION."),
    "dateline": "WASHINGTON / TEHRAN - 19 NOV",
}

# (headline, summary, location) — headlines fit one line at scale 2.
STORIES = [
    ("TRUMP, XI AND PUTIN DUE TO MEET",
     "THE THREE LEADERS ARE DUE TO HOLD TRILATERAL TALKS ON THE SIDELINES OF THE APEC SUMMIT IN SHENZHEN.",
     "SHENZHEN"),
    ("JEFFRIES NOMINATED AS US HOUSE SPEAKER",
     "DEMOCRATS NOMINATE HAKEEM JEFFRIES, SET TO BECOME THE FIRST AFRICAN-AMERICAN SPEAKER OF THE HOUSE.",
     "WASHINGTON"),
    ("GTA VI ROLLS OUT AFTER 13-YEAR WAIT",
     "GAMERS ENTER VICE CITY AS GRAND THEFT AUTO VI BEGINS ITS GLOBAL ROLLOUT, 13 YEARS AFTER GTA V.",
     "WORLD"),
    ("EU PROPOSES 45BN EURO LOAN FOR KYIV",
     "BRUSSELS PLANS A 45 BILLION EURO LOAN TO UKRAINE, TO BE REPAID AFTER RUSSIA PAYS REPARATIONS.",
     "BRUSSELS"),
    ("VOYAGER 1 REACHES ONE LIGHT-DAY",
     "NASA SAYS THE 49-YEAR-OLD PROBE HAS FLOWN A LIGHT-DAY FROM EARTH, A FIRST FOR ANY SPACECRAFT.",
     "SPACE"),
    ("AKVAN NEARS ANDHRA COAST",
     "THE CYCLONE OVER THE BAY OF BENGAL NEARS THE ANDHRA COAST; LANDFALL IS DUE ON 20 NOV, FORECASTERS SAY.",
     "INDIA"),
    ("NVIDIA HALTS H-SERIES CHIPS TO CHINA",
     "THE CHIPMAKER SAYS IT NO LONGER SHIPS HOPPER CHIPS TO MAINLAND CHINA, ITS INTERIM CEO TELLS INVESTORS.",
     "TECH"),
    ("FED MINUTES POINT TO MORE RATE HIKES",
     "MOST FED OFFICIALS EXPECT FURTHER HIKES IF INFLATION AND JOBS DEVELOP AS EXPECTED, MINUTES SHOW.",
     "WASHINGTON"),
    ("ONE NATION SLASHES REFUGEE PLAN",
     "AUSTRALIA'S ONE NATION PLANS TO CUT THE REFUGEE INTAKE BY 90 PERCENT, FROM 20,000 TO 2,000 PLACES A YEAR.",
     "CANBERRA"),
    ("CANADA RETHINKS CHINA TIES, PM SAYS",
     "CARNEY SAYS OTTAWA IS ADJUSTING ITS CHINA POLICY WHILE SEEKING THE RIGHT DEAL WITH WASHINGTON.",
     "SHENZHEN"),
    ("SENATORS WARN OF AI CYBER THREATS",
     "US SENATORS TELL THE WHITE HOUSE THAT AI-ENABLED CYBER ATTACKS ARE OUTPACING AMERICAN DEFENCES.",
     "WASHINGTON"),
    ("RUSSIA ACCUSES FRANCE OVER UKRAINE",
     "FRANCE ADMITS A SMALL TRAINING FORCE IN UKRAINE BUT DENIES ANY COMBAT ROLE.",
     "MOSCOW"),
    ("BRAZIL SENATE PASSES FISCAL PACKAGE",
     "THE BILL AIMS TO IMPROVE PUBLIC FINANCES BY UP TO 60 BILLION REAIS IN 2027 AND NOW GOES TO THE LOWER HOUSE.",
     "BRASILIA"),
    ("ARGENTINA ROUT COSTA RICA 7-0",
     "IN THE POST-MESSI ERA, ARGENTINA THRASH COSTA RICA 7-0 IN THEIR LAST FRIENDLY OF 2026, WITH THREE PLAYERS SCORING TWICE.",
     "CORDOBA"),
    ("INDIA AND JAPAN HOLD 2+2 TALKS",
     "THE TWO COUNTRIES REVIEW DEFENCE TIES AND STRATEGIC COOPERATION IN A MINISTERIAL DIALOGUE.",
     "TOKYO"),
    ("AMAZON PLEDGES 7BN DOLLARS FOR INDIA",
     "AMAZON WILL INVEST 7 BILLION DOLLARS IN RENEWABLE ENERGY PROJECTS IN INDIA BY 2030.",
     "NEW DELHI"),
    ("MODI MEETS PRINCE AND PRINCESS OF WALES",
     "INDIA'S PM DISCUSSES BOOSTING UK-INDIA TIES WITH THE ROYAL COUPLE IN NEW DELHI.",
     "NEW DELHI"),
    ("ISLAM SET TO BE LARGEST FAITH BY 2035",
     "A PEW REPORT PROJECTS ISLAM WILL OVERTAKE CHRISTIANITY AS THE WORLD'S LARGEST RELIGION BY 2035.",
     "WORLD"),
    ("SOMALIA ACCUSES UAE OF SECRET BASES",
     "MOGADISHU SAYS THE UAE BUILT MILITARY BASES ON ITS SOIL WITHOUT APPROVAL AND BACKS ARMED GROUPS.",
     "MOGADISHU"),
    ("HUGE DRUG HAUL SEIZED IN EAST LIBYA",
     "COCAINE AND MILLIONS OF PILLS ARE SEIZED BY OFFICIALS IN EASTERN LIBYA.",
     "LIBYA"),
    ("AIRSTRIKES KILL 21 ISWAP FIGHTERS",
     "AIRSTRIKES KILL 21 SUSPECTED ISWAP FIGHTERS IN BORNO STATE, THE ARMY SAYS.",
     "NIGERIA"),
    ("MOROCCO SETS DEFENCE INDUSTRY GOAL",
     "RABAT'S ROADMAP TARGETS 50,000 DEFENCE JOBS AND 65 PERCENT EXPORT REVENUE BY 2035.",
     "RABAT"),
    ("QUAD LAUNCHES AI ACCELERATOR",
     "QUAD LEADERS IN MANILA LAUNCH AN 85 MILLION DOLLAR AI ACCELERATOR; AUSTRALIA ALSO BACKS A US-LED AI SUPPLY PACT.",
     "MANILA"),
    ("AUSTRALIA SANCTIONS SETTLEMENTS",
     "FOREIGN MINISTER WONG ANNOUNCES FRESH SANCTIONS OVER ILLEGAL ISRAELI SETTLEMENT EXPANSION ON THE WEST BANK.",
     "CANBERRA"),
    ("PNG APPLICATIONS OPEN FOR ADF",
     "PAPUA NEW GUINEANS CAN NOW APPLY TO JOIN AUSTRALIA'S DEFENCE FORCE UNDER A NEW BILATERAL DEAL.",
     "CANBERRA"),
    ("POLICE CLASH AS SPAIN STRIKES",
     "POLICE CLASH WITH PROTESTERS AS WORKERS STRIKE ACROSS SPAIN.",
     "MADRID"),
    ("DEUTSCHE BANK AND 582M EPSTEIN DEALS",
     "THE BANK FLAGGED 582 MILLION DOLLARS IN SUSPICIOUS EPSTEIN-LINKED DEALS FROM OCT 2013 TO MAY 2019.",
     "FRANKFURT"),
    ("MELENCHON COULD WIN RUNOFF",
     "DARMANIN SAYS THE HARD-LEFT LEADER COULD WIN THE SECOND ROUND IF HE FACES LE PEN; POLLS FAVOUR LE PEN.",
     "PARIS"),
    ("SAUDI ARABIA SAYS DANGER HAS PASSED",
     "RIYADH SAYS THE DANGER HAS PASSED IN THREE SOUTHERN CITIES AFTER HOUTHI MISSILE AND DRONE ATTACKS.",
     "RIYADH"),
    ("INDIA BEAT PAKISTAN IN SAFF FINAL",
     "INDIA WIN THE SAFF CHAMPIONSHIP FINAL 2-1 AGAINST PAKISTAN IN DHAKA.",
     "DHAKA"),
    ("GOLD HITS 14-MONTH LOW",
     "GOLD PLUNGES BELOW 3,800 DOLLARS TO A 14-MONTH LOW AS A STRONGER DOLLAR AND FED RATE BETS WEIGH ON MARKETS.",
     "MARKETS"),
    ("VAPING LINKED TO LUNG DECLINE",
     "A SMALL STUDY OF 22 VAPERS FINDS A ONE-YEAR FALL IN LUNG FUNCTION; RESEARCHERS SAY LARGER STUDIES ARE NEEDED.",
     "HEALTH"),
    ("DATA CENTRES COULD RIVAL COAL",
     "AUSTRALIA'S NINE DIRTIEST DATA CENTRE PROPOSALS COULD ADD 40 MILLION TONNES OF CLIMATE POLLUTION A YEAR BY 2035.",
     "AUSTRALIA"),
]

NUMBERS = [
    ("3", "US CARRIERS NOW IN THE GULF"),
    ("45BN", "EURO LOAN PROPOSED FOR KYIV"),
    ("13", "YEARS SINCE THE LAST GTA"),
    ("1", "LIGHT-DAY: VOYAGER 1 DISTANCE"),
    ("83.26", "WTI CRUDE, 18 NOV CLOSE"),
    ("7-0", "ARGENTINA ROUT COSTA RICA"),
]


# ---------------------------------------------------------------- layout
def _lerp(a, b, t):
    return int(round(a + (b - a) * t))


def _mix(c1, c2, t):
    return (_lerp(c1[0], c2[0], t), _lerp(c1[1], c2[1], t),
            _lerp(c1[2], c2[2], t))


def draw_masthead():
    draw_text_centered("THE WORLD TODAY", 512, 18, 6, 3, INK)
    hline(20, 66, 984, INK, 2)
    hline(20, 71, 984, INK, 1)
    draw_text("VOL. 1 - NO. 323", 20, 78, 1, 1, GREY)
    draw_text_centered("THURSDAY 19 NOVEMBER 2026", 512, 76, 2, 2, NAVY)
    rt = "PRICE: FREE"
    draw_text(rt, 1004 - text_w(rt, 1), 78, 1, 1, GREY)


def draw_hero_art(x0, y0, w, h):
    horizon = y0 + 110
    for yy in range(y0, horizon):
        t = (yy - y0) / max(1, horizon - y0)
        fill_rect(x0, yy, w, 1, _mix(SKY_TOP, SKY_LOW, t))
    for yy in range(horizon, y0 + h):
        t = (yy - horizon) / max(1, y0 + h - horizon)
        fill_rect(x0, yy, w, 1, _mix(SEA_TOP, SEA_BOT, t))
    # clouds
    for (cx, cy, cw) in [(x0 + 60, y0 + 26, 120), (x0 + 250, y0 + 14, 90),
                         (x0 + 480, y0 + 78, 60)]:
        fill_rect(cx, cy, cw, 10, (226, 231, 238))
        fill_rect(cx + 14, cy - 6, cw - 40, 8, (226, 231, 238))
    # sun
    filled_circle(x0 + 440, y0 + 34, 26, SUN)
    circle_outline(x0 + 440, y0 + 34, 30, (240, 200, 110), 2)
    # birds
    for (bx, by) in [(x0 + 170, y0 + 44), (x0 + 205, y0 + 34),
                     (x0 + 238, y0 + 50)]:
        line(bx - 7, by, bx, by + 5, INK, 2)
        line(bx, by + 5, bx + 7, by, INK, 2)
    # missile trails with smoke dots, launched from the ships
    for k in range(11):
        px = x0 + 115 + k * 14
        py = horizon - 8 - k * 7
        if k % 2 == 0:
            filled_circle(px, py, 3, WHITE)
    line(x0 + 115, horizon - 8, x0 + 269, horizon - 78, (240, 120, 60), 2)
    for k in range(9):
        px = x0 + 388 + k * 13
        py = horizon - 4 - k * 7
        if k % 2 == 0:
            filled_circle(px, py, 3, WHITE)
    line(x0 + 388, horizon - 4, x0 + 492, horizon - 60, (240, 120, 60), 2)
    # explosion burst at the end of the first trail
    ex, ey = x0 + 271, horizon - 80
    filled_circle(ex, ey, 7, (255, 190, 60))
    for (dx, dy) in [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1),
                     (1, -1), (-1, 1)]:
        line(ex, ey, ex + dx * 15, ey + dy * 15, (220, 80, 30), 2)
    # warship 1
    fill_rect(x0 + 50, horizon + 2, 130, 16, NAVY_DARK)
    fill_rect(x0 + 42, horizon + 2, 16, 8, NAVY_DARK)
    fill_rect(x0 + 82, horizon - 14, 44, 16, NAVY_DARK)
    line(x0 + 100, horizon - 30, x0 + 100, horizon - 14, NAVY_DARK, 3)
    fill_rect(x0 + 100, horizon - 30, 14, 9, RED)
    # warship 2
    fill_rect(x0 + 330, horizon + 6, 100, 13, NAVY_DARK)
    fill_rect(x0 + 322, horizon + 6, 12, 7, NAVY_DARK)
    fill_rect(x0 + 358, horizon - 8, 30, 14, NAVY_DARK)
    line(x0 + 372, horizon - 22, x0 + 372, horizon - 8, NAVY_DARK, 3)
    # caption strip
    fill_rect(x0, y0 + h - 20, w, 20, NAVY_DARK)
    draw_text_centered("US WARSHIPS IN THE GULF - 19 NOV", x0 + w // 2,
                       y0 + h - 14, 1, 1, WHITE)


def draw_hero():
    rect_border(14, 96, 996, 212, INK, 2)
    draw_hero_art(20, 102, 540, 170)
    tx = 576
    draw_text(HERO["kicker"], tx, 108, 1, 1, RED)
    lines = wrap_lines(HERO["headline"], 3, 428, 428)
    cy = 124
    for ln in lines:
        draw_text(ln, tx, cy, 3, 2, INK)
        cy += 23
    hline(tx, cy + 2, 428, RED, 2)
    cy += 12
    draw_wrapped(HERO["standfirst"], tx, cy, 1, 1, INK, 428, 428, 6, 9)
    draw_text(HERO["dateline"], tx, 240, 1, 1, GREY)
    # inside-today strip across the hero bottom
    hline(20, 282, 984, GREY, 1)
    draw_text_centered(
        "INSIDE TODAY: GTA VI ARRIVES - JEFFRIES NOMINATED - "
        "VOYAGER 1 HITS ONE LIGHT-DAY",
        512, 292, 1, 1, NAVY)


def draw_story(idx, headline, summary, loc, x, y, col_w, sum_y, line_h):
    fill_rect(x, y + 1, 16, 16, RED)
    num = str(idx)
    draw_text_centered(num, x + 8, y + 5, 1, 1, WHITE)
    draw_text(headline, x + 22, y + 2, 2, 2, INK)
    draw_wrapped(summary, x, y + sum_y, 1, 1, INK, col_w, col_w, 2, line_h,
                 first_color=RED, first_prefix=loc + " - ")


def draw_stories():
    draw_text_centered("THE WORLD IN BRIEF - 33 STORIES", 512, 316, 2, 2,
                       NAVY)
    hline(20, 334, 984, INK, 2)
    col_w = 482
    y0 = 340
    left = STORIES[:16]
    right = STORIES[16:]
    for i, (hd, sm, lc) in enumerate(left):
        y = y0 + i * 36
        if i % 2 == 0:
            fill_rect(20, y, col_w, 36, PAPER_DARK)
        draw_story(i + 1, hd, sm, lc, 20, y, col_w, 18, 8)
    for i, (hd, sm, lc) in enumerate(right):
        y = y0 + i * 34
        if i % 2 == 0:
            fill_rect(522, y, col_w, 34, PAPER_DARK)
        draw_story(17 + i, hd, sm, lc, 522, y, col_w, 18, 8)
    vline(512, 340, 578, (200, 194, 178), 1)


def draw_numbers():
    hline(20, 924, 984, INK, 2)
    draw_text("BY THE NUMBERS", 20, 932, 2, 2, NAVY)
    cell_w = 996 // 6
    for i, (big, label) in enumerate(NUMBERS):
        cx = 14 + i * cell_w
        if i > 0:
            vline(cx, 952, 56, (200, 194, 178), 1)
        draw_text_centered(big, cx + cell_w // 2, 952, 2, 2, RED)
        lines = wrap_lines(label, 1, cell_w - 12, cell_w - 12)
        ly = 972
        for ln in lines[:2]:
            draw_text_centered(ln, cx + cell_w // 2, ly, 1, 1, INK)
            ly += 9


def build():
    fill_rect(0, 0, W, H, PAPER)
    grain(1)
    rect_border(8, 8, 1008, 1008, INK, 2)
    draw_masthead()
    draw_hero()
    draw_stories()
    draw_numbers()
    return png_bytes()


def main():
    out = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(out, exist_ok=True)
    data = build()
    with open(os.path.join(out, "entry.png"), "wb") as f:
        f.write(data)


if __name__ == "__main__":
    main()
