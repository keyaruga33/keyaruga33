from pathlib import Path
from html import escape

SKILLS = {
    "Python Ecosystem": 94,
    "Backend Development": 90,
    "Mobile (Flutter)": 85,
    "Frontend Web": 75,
    "Databases": 78,
    "Desktop (Qt/QML)": 72,
     "Linux & DevOps": 70,
    "DevOps & Infrastructure": 70,
    "Go": 65,
}

OUTPUT_FILE = "../assets/section/skills.svg"

WIDTH = 900
BAR_WIDTH = 820
ROW_HEIGHT = 54
TOP = 70
BOTTOM = 20
HEIGHT = TOP + len(SKILLS) * ROW_HEIGHT + BOTTOM


def generate_svg(skills):
    if not skills:
        raise ValueError("SKILLS cannot be empty.")

    for name, pct in skills.items():
        if not isinstance(pct, (int, float)):
            raise TypeError(f"{name}: percentage must be a number.")
        if not 0 <= pct <= 100:
            raise ValueError(f"{name}: percentage must be between 0 and 100.")

    animations = []
    rows = []

    for i, (name, pct) in enumerate(skills.items()):
        width = BAR_WIDTH * pct / 100
        y = i * ROW_HEIGHT

        animations.append("""
    @keyframes grow{0} {{
      0%,4% {{ width:0; }}
      55% {{ width:{1:.2f}px; }}
      100% {{ width:{1:.2f}px; }}
    }}
    .b{0} {{
      animation:
        grow{0} 3.2s cubic-bezier(.2,.8,.2,1) 1 forwards,
        shimmer 3s ease-in-out infinite 3.2s;
    }}
""".format(i, width))

        rows.append("""
      <g transform="translate(0,{0})">
        <text y="0">{1}</text>
        <text x="{2}" y="0" text-anchor="end" class="pct">{3:g}%</text>
        <rect class="track" y="14" width="{2}" height="10" rx="5"/>
        <rect class="b{4}" y="14" width="0" height="10" rx="5"
              fill="url(#barGrad)" filter="url(#barGlow)"/>
      </g>
""".format(y, escape(str(name)), BAR_WIDTH, pct, i))

    return """<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="barGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#00D9CB"/>
      <stop offset="60%" stop-color="#109EE6"/>
      <stop offset="100%" stop-color="#BD49FF"/>
    </linearGradient>
    <filter id="barGlow" x="-30%" y="-100%" width="160%" height="300%">
      <feGaussianBlur stdDeviation="4" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <clipPath id="skClip"><rect width="{width}" height="{height}" rx="14"/></clipPath>
  </defs>

  <style>
    text {{ font:500 15px 'Consolas','Fira Code',monospace; fill:#DCF0FF; }}
    .lbl {{ fill:#A0B4CC; }}
    .pct {{ fill:#5AFFF0; font-weight:700; }}
    .track {{ fill:#1E2436; }}

    @keyframes shimmer {{
      0%,100% {{ opacity:1; }}
      50% {{ opacity:0.78; }}
    }}

    .head {{ animation:headBlink 2.4s ease-in-out infinite; }}

    @keyframes headBlink {{
      0%,100% {{ opacity:1; }}
      50% {{ opacity:0.4; }}
    }}

    .flick {{ animation:fBorder2 6s steps(24) infinite; }}

    @keyframes fBorder2 {{
      0%,100% {{ opacity:0.8; }}
      40% {{ opacity:0.3; }}
      42% {{ opacity:0.8; }}
    }}
{animations}
  </style>

  <g clip-path="url(#skClip)">
    <rect width="{width}" height="{height}" fill="#0E1424"/>
    <rect width="{width}" height="34" fill="#080D19"/>
    <circle class="head" cx="20" cy="17" r="5" fill="#00D9CB"/>
    <text x="34" y="22" class="lbl">tech_stack.log</text>
    <line x1="0" y1="34" x2="{width}" y2="34" stroke="#1E3448"/>

    <g transform="translate(28,70)">
{rows}
    </g>

    <rect class="flick" x="1" y="1" width="{inner_width}" height="{inner_height}"
          rx="13" fill="none" stroke="#BD49FF" stroke-width="1.5"/>
  </g>
</svg>
""".format(
        width=WIDTH,
        height=HEIGHT,
        inner_width=WIDTH - 2,
        inner_height=HEIGHT - 2,
        animations="".join(animations),
        rows="".join(rows),
    )


if __name__ == "__main__":
    Path(OUTPUT_FILE).write_text(generate_svg(SKILLS), encoding="utf-8")
    print(f"Generated: {OUTPUT_FILE}")
