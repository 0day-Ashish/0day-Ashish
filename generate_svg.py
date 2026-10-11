"""
Builds dark_mode.svg and light_mode.svg from a photo and the profile info below.
Run this locally whenever the photo or the static info changes:

    python3 generate_svg.py                 # uses the current GitHub avatar
    python3 generate_svg.py photo.jpg       # uses a local image instead
    python3 generate_svg.py photo.jpg 0.25  # ...cropped around 25% from the left edge

The photo is resized, re-encoded without metadata (EXIF/GPS) and embedded as base64,
since GitHub does not load external images inside SVGs.

Requires Pillow (pip install pillow). The numbers under "GitHub Stats" are placeholders,
today.py (run daily by GitHub Actions) fills them in by element id.
"""
import base64
import io
import sys
import urllib.request
from xml.sax.saxutils import escape
from PIL import Image, ImageOps

USER_NAME = '0day-Ashish'

# ---- Layout ---------------------------------------------------------------
WIDTH = 1040
PAD = 30
TOP = 66                 # first text baseline, below the title bar
LINE_H = 18              # info line height
FONT_SIZE = 14
COLS = 70                # characters per info line (rules are drawn to this width)
VALUE_COL = 26           # column where values start

PHOTO_W = 331
PHOTO_TOP = TOP - 14
TEXT_X = PAD + PHOTO_W + 30

# ---- Content --------------------------------------------------------------
# (key, value) rows, '.' is an empty spacer row, ('#', title) a section header
INFO = [
    ('OS', 'macOS, Linux, iOS, Android'),
    ('Uptime', None),
    ('Host', 'Bengaluru, India'),
    ('Kernel', 'Designer & Full Stack Developer'),
    ('IDE', 'Cursor, VSCode, Android Studio'),
    ('Hobbies', 'Web3, UI/UX, Frontend'),
    '.',
    ('Languages.Programming', 'TypeScript, JavaScript, Python, Solidity'),
    ('Languages.Computer', 'HTML, CSS, JSON, SQL, GraphQL'),
    ('Languages.Real', 'English, Hindi'),
    ('Stack.Frontend', 'React, Next.js, Tailwind CSS, GSAP, Three.js'),
    ('Stack.Backend', 'Node.js, PostgreSQL, MongoDB'),
    ('Stack.Cloud', 'Vercel, Railway, Render'),
    '.',
    ('#', 'Projects'),
    ('Building', 'seerix.ai, Builder House'),
    ('Featured', 'broskie.ai, Zero UI, Kryptos, Signifiya'),
    ('Certified', 'Claude 101 (Anthropic), Frontend (HackerRank)'),
    '.',
    ('#', 'Contact'),
    ('Email.Personal', '0day.ashish@gmail.com'),
    ('Website', 'arddev.in'),
    ('LinkedIn', 'linkedin.com/in/arddev'),
    ('GitHub', 'github.com/0day-Ashish'),
    ('X', 'x.com/Ashishrd06'),
    ('Instagram', 'instagram.com/ashishhikr'),
    '.',
    ('#', 'GitHub Stats'),
    'stats',
]

THEMES = {
    'dark': dict(bg='#0d1117', card='#161b22', border='#30363d', text='#c9d1d9', key='#ffa657',
                 value='#a5d6ff', cc='#616e7f', add='#3fb950', dele='#f85149', user='#7ee787',
                 section='#d2a8ff', bar='#21262d'),
    'light': dict(bg='#ffffff', card='#f6f8fa', border='#d0d7de', text='#24292f', key='#953800',
                  value='#0a3069', cc='#8c959f', add='#1a7f37', dele='#cf222e', user='#116329',
                  section='#8250df', bar='#eaeef2'),
}
PALETTE = ['#f85149', '#ffa657', '#e3b341', '#3fb950', '#39c5cf', '#58a6ff', '#bc8cff', '#c9d1d9']


def photo_data_uri(image, photo_h, focus_x=0.5):
    """
    Crops the photo to the panel's aspect ratio around focus_x and returns it as a JPEG data URI
    """
    im = ImageOps.exif_transpose(image).convert('RGB')
    w, h = im.size
    aspect = PHOTO_W / photo_h
    if w / h > aspect:
        crop_w = int(h * aspect)
        x0 = max(0, min(w - crop_w, int(w * focus_x - crop_w / 2)))
        im = im.crop((x0, 0, x0 + crop_w, h))
    else:
        crop_h = int(w / aspect)
        im = im.crop((0, (h - crop_h) // 2, w, (h - crop_h) // 2 + crop_h))
    im = im.resize((PHOTO_W * 2, int(photo_h * 2)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=82, optimize=True, progressive=True)  # no exif= so metadata is dropped
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()


def dots(prefix_len):
    """
    Dot leader that moves the value to VALUE_COL, e.g. ' ........ '
    """
    fill = VALUE_COL - prefix_len
    return ' ' * fill if fill <= 2 else ' ' + '.' * (fill - 2) + ' '


def key_markup(key):
    return '.'.join(f'<tspan class="key">{escape(k)}</tspan>' for k in key.split('.'))


def rule(title_len):
    return ' ' + '—' * (COLS - title_len - 1)


def info_lines():
    """
    Returns the inner markup of every info row (positioned later)
    """
    rows = []
    for item in INFO:
        if item == '.':
            rows.append('<tspan class="cc">. </tspan>')
        elif item == 'stats':
            rows += [
                '<tspan class="cc">. </tspan><tspan class="key">Repos</tspan>:<tspan class="cc" id="repo_data_dots"> .... </tspan><tspan class="value" id="repo_data">0</tspan> {<tspan class="key">Contributed</tspan>: <tspan class="value" id="contrib_data">0</tspan>} | <tspan class="key">Stars</tspan>:<tspan class="cc" id="star_data_dots"> ........... </tspan><tspan class="value" id="star_data">0</tspan>',
                '<tspan class="cc">. </tspan><tspan class="key">Commits</tspan>:<tspan class="cc" id="commit_data_dots"> ................. </tspan><tspan class="value" id="commit_data">0</tspan> | <tspan class="key">Followers</tspan>:<tspan class="cc" id="follower_data_dots"> ....... </tspan><tspan class="value" id="follower_data">0</tspan>',
                '<tspan class="cc">. </tspan><tspan class="key">Lines of Code on GitHub</tspan>:<tspan class="cc" id="loc_data_dots">. </tspan><tspan class="value" id="loc_data">0</tspan> ( <tspan class="addColor" id="loc_add">0</tspan><tspan class="addColor">++</tspan>, <tspan id="loc_del_dots"> </tspan><tspan class="delColor" id="loc_del">0</tspan><tspan class="delColor">--</tspan> )',
            ]
        elif item[0] == '#':
            rows.append(f'<tspan class="section">— {escape(item[1])}</tspan><tspan class="cc">{rule(len(item[1]) + 2)}</tspan>')
        else:
            key, value = item
            if value is None:  # uptime, filled in by today.py
                rows.append(f'<tspan class="cc">. </tspan>{key_markup(key)}:<tspan class="cc" id="age_data_dots">{dots(len(key) + 3)}</tspan><tspan class="value" id="age_data">0 years</tspan>')
            else:
                rows.append(f'<tspan class="cc">. </tspan>{key_markup(key)}:<tspan class="cc">{dots(len(key) + 3)}</tspan><tspan class="value">{escape(value)}</tspan>')
    return rows


def panel_height():
    return TOP + LINE_H * len(info_lines()) + 6 - PHOTO_TOP


def build(theme, photo):
    t = THEMES[theme]
    rows = info_lines()
    text_bottom = TOP + LINE_H * (len(rows) + 1)
    height = text_bottom + PAD
    photo_h = panel_height()

    out = [f'''<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,'SF Mono',Menlo,monospace" width="{WIDTH}px" height="{height:.0f}px" font-size="{FONT_SIZE}px">
<style>
@font-face {{
src: local('Consolas'), local('Consolas Bold');
font-family: 'ConsolasFallback';
font-display: swap;
-webkit-size-adjust: 109%;
size-adjust: 109%;
}}
.key {{fill: {t['key']};}}
.value {{fill: {t['value']};}}
.addColor {{fill: {t['add']};}}
.delColor {{fill: {t['dele']};}}
.cc {{fill: {t['cc']};}}
.user {{fill: {t['user']};}}
.section {{fill: {t['section']};}}
.cursor {{animation: blink 1.1s steps(1) infinite;}}
@keyframes blink {{ 50% {{ opacity: 0; }} }}
text, tspan {{white-space: pre;}}
</style>
<defs>
<clipPath id="photoClip"><rect x="{PAD}" y="{PHOTO_TOP}" width="{PHOTO_W}" height="{photo_h}" rx="10"/></clipPath>
</defs>
<rect width="{WIDTH}px" height="{height:.0f}px" fill="{t['card']}" stroke="{t['border']}" rx="12"/>
<path d="M12 0.5 H{WIDTH - 12} A11.5 11.5 0 0 1 {WIDTH - 0.5} 12 V36 H0.5 V12 A11.5 11.5 0 0 1 12 0.5 Z" fill="{t['bar']}"/>
<line x1="0.5" y1="36" x2="{WIDTH - 0.5}" y2="36" stroke="{t['border']}"/>
<circle cx="22" cy="18" r="6" fill="#ff5f56"/>
<circle cx="42" cy="18" r="6" fill="#ffbd2e"/>
<circle cx="62" cy="18" r="6" fill="#27c93f"/>
<text x="{WIDTH / 2:.0f}" y="23" text-anchor="middle" font-size="13px" class="cc">ashish@arddev.in: ~ — neofetch</text>''']

    out.append(f'<image x="{PAD}" y="{PHOTO_TOP}" width="{PHOTO_W}" height="{photo_h}" preserveAspectRatio="xMidYMid slice" clip-path="url(#photoClip)" href="{photo}"/>')
    out.append(f'<rect x="{PAD}" y="{PHOTO_TOP}" width="{PHOTO_W}" height="{photo_h}" rx="10" fill="none" stroke="{t["border"]}"/>')

    out.append(f'<text x="{TEXT_X}" y="{TOP}" fill="{t["text"]}">')
    out.append(f'<tspan x="{TEXT_X}" y="{TOP}"><tspan class="user">ashish</tspan>@<tspan class="value">arddev.in</tspan></tspan><tspan class="cc">{rule(16)}</tspan>')
    for i, row in enumerate(rows, start=1):
        out.append(row.replace('<tspan', f'<tspan x="{TEXT_X}" y="{TOP + i * LINE_H}"', 1))
    out.append('</text>')

    # neofetch colour blocks + blinking cursor
    y = TOP + (len(rows) + 1) * LINE_H - 12
    for i, c in enumerate(PALETTE):
        out.append(f'<rect x="{TEXT_X + 12 + i * 26}" y="{y}" width="22" height="14" rx="2" fill="{c}"/>')
    out.append(f'<rect class="cursor" x="{TEXT_X + 12 + len(PALETTE) * 26 + 6}" y="{y}" width="9" height="16" fill="{t["text"]}"/>')
    out.append('</svg>\n')
    return '\n'.join(out)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        avatar = Image.open(sys.argv[1])
    else:
        with urllib.request.urlopen(f'https://github.com/{USER_NAME}.png?size=800') as r:
            avatar = Image.open(io.BytesIO(r.read()))
    focus_x = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
    photo = photo_data_uri(avatar, panel_height(), focus_x)
    for theme in THEMES:
        with open(f'{theme}_mode.svg', 'w', encoding='utf-8') as f:
            f.write(build(theme, photo))
    print(f'embedded photo: {len(photo) // 1024} KB')
