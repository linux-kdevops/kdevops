# SPDX-License-Identifier: copyleft-next-0.3.1
"""HTML report template and section helpers.

A workflow adapter builds a Report by adding stat-cards (the header
KPI grid), sections (each section a title + body HTML), and optionally
a monitoring section. The template is self-contained: charts are
embedded as base64 data URIs so the output HTML works without any
sibling files.
"""

from __future__ import annotations

import base64
import dataclasses
import re
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Optional

# CSS lifted from build-linux's visualize_results.py demo, generalized
# to not name a specific workflow in the template. Adapters set the
# heading text via Report.title.
_CSS = """
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    margin: 0;
    padding: 20px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
}
.container {
    max-width: 1400px;
    margin: 0 auto;
    background: white;
    border-radius: 10px;
    padding: 30px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
}
h1 {
    color: #2d3748;
    text-align: center;
    font-size: 2.2em;
    margin-bottom: 10px;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
}
.timestamp {
    text-align: center;
    color: #718096;
    margin-bottom: 30px;
    font-size: 0.9em;
}
.summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin: 30px 0;
}
.stat-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 20px;
    border-radius: 10px;
    text-align: center;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}
.stat-value { font-size: 2em; font-weight: bold; margin: 10px 0; }
.stat-label { font-size: 0.9em; opacity: 0.9; }
.section { margin: 40px 0; }
.section-title {
    font-size: 1.6em;
    color: #2d3748;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 3px solid #667eea;
}
.toc {
    margin: 24px 0;
    padding: 18px 22px;
    background: #f7fafc;
    border-left: 4px solid #667eea;
    border-radius: 6px;
}
.toc-title {
    font-size: 1.1em;
    color: #2d3748;
    margin-bottom: 8px;
    font-weight: 600;
}
.toc ul { list-style: none; padding-left: 0; margin: 0; }
.toc > ul > li { margin: 6px 0; }
.toc ul ul { padding-left: 18px; margin: 4px 0; }
.toc ul ul ul { padding-left: 16px; }
.toc a {
    color: #4a5568;
    text-decoration: none;
    border-bottom: 1px dotted transparent;
}
.toc a:hover { color: #667eea; border-bottom-color: #667eea; }
.toc-l1 { font-weight: 600; color: #2d3748; }
.back-to-toc {
    text-align: right;
    margin-top: 24px;
    font-size: 0.9em;
}
.back-to-toc a {
    color: #667eea;
    text-decoration: none;
    padding: 4px 10px;
    border: 1px solid #cbd5e0;
    border-radius: 4px;
    background: #f7fafc;
}
.back-to-toc a:hover {
    background: #667eea;
    color: white;
    border-color: #667eea;
}
.chart-container {
    margin: 20px 0;
    padding: 16px;
    background: #f7fafc;
    border-radius: 8px;
}
.chart { text-align: center; }
.chart img { max-width: 100%; border-radius: 5px; }
table {
    width: 100%;
    border-collapse: collapse;
    margin: 16px 0;
    background: white;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 4px rgba(0,0,0,0.06);
}
th {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 12px;
    text-align: left;
    font-weight: 600;
}
td { padding: 10px 12px; border-bottom: 1px solid #e2e8f0; }
tr:hover { background: #f7fafc; }
tr:last-child td { border-bottom: none; }
.success { color: #48bb78; font-weight: bold; }
.failure { color: #f56565; font-weight: bold; }
.no-data {
    text-align: center;
    padding: 40px;
    color: #718096;
    font-style: italic;
}
"""


@dataclasses.dataclass
class StatCard:
    label: str
    value: str


@dataclasses.dataclass
class Section:
    title: str
    body_html: str


@dataclasses.dataclass
class Report:
    title: str
    stat_cards: list[StatCard] = dataclasses.field(default_factory=list)
    sections: list[Section] = dataclasses.field(default_factory=list)
    timestamp: Optional[datetime] = None

    def add_card(self, label: str, value: str) -> None:
        self.stat_cards.append(StatCard(label=label, value=value))

    def add_section(self, title: str, body_html: str) -> None:
        self.sections.append(Section(title=title, body_html=body_html))


def embed_png(png_bytes: bytes) -> str:
    """Encode raw PNG bytes as a data URI for inline embedding."""
    b64 = base64.b64encode(png_bytes).decode()
    return f"data:image/png;base64,{b64}"


def embed_png_file(path: Path) -> Optional[str]:
    """Read a PNG file and return its data URI; None if absent."""
    if not path.exists():
        return None
    return embed_png(path.read_bytes())


def chart_block(image_data_uri: Optional[str], no_data_msg: str = "Chart not available") -> str:
    """Wrap a base64 image (or a no-data message) in chart-container HTML."""
    if not image_data_uri:
        return f'<div class="no-data">{escape(no_data_msg)}</div>'
    return (
        '<div class="chart-container">'
        f'<div class="chart"><img src="{image_data_uri}" /></div>'
        '</div>'
    )


_SLUG_NON_WORD = re.compile(r"[^a-z0-9]+")


def _slugify(text: str, used: set[str]) -> str:
    """Lowercase ASCII slug; suffix with -2/-3/... when colliding."""
    base = _SLUG_NON_WORD.sub("-", text.lower()).strip("-") or "section"
    slug = base
    n = 2
    while slug in used:
        slug = f"{base}-{n}"
        n += 1
    used.add(slug)
    return slug


_HEADING_RE = re.compile(
    r"<(h[234])(\b[^>]*)>(.+?)</\1>",
    re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")


def _inject_ids_and_collect(
    body_html: str,
    used_slugs: set[str],
) -> tuple[str, list[tuple[int, str, str]]]:
    """Add id="..." to every h2/h3/h4 in body_html that lacks one.

    Returns (new_body, [(level, id, plain_text), ...]) for TOC building.
    Headings that already have an id keep theirs.
    """
    entries: list[tuple[int, str, str]] = []

    def replace(match: re.Match) -> str:
        tag = match.group(1)
        attrs = match.group(2) or ""
        inner = match.group(3)
        plain = _TAG_RE.sub("", inner).strip()
        existing = re.search(r'\bid="([^"]+)"', attrs)
        if existing:
            heading_id = existing.group(1)
            new_attrs = attrs
        else:
            heading_id = _slugify(plain, used_slugs)
            new_attrs = f'{attrs} id="{heading_id}"'
        entries.append((int(tag[1]), heading_id, plain))
        return f"<{tag}{new_attrs}>{inner}</{tag}>"

    new_body = _HEADING_RE.sub(replace, body_html)
    return new_body, entries


def _render_toc(entries: list[tuple[int, str, str]]) -> str:
    """Render an HTML <nav class="toc"> from a flat heading list.

    Headings are nested by level so the TOC reads like a tree. The
    top of the list is treated as level 2 (h2 == top-level section).
    """
    if not entries:
        return ""

    parts: list[str] = []
    parts.append('<nav class="toc" id="contents">')
    parts.append('<div class="toc-title">📋 Contents</div>')
    parts.append("<ul>")

    current_level = 2
    open_lis = 0  # Track open <li>s at current_level

    for level, slug, text in entries:
        # Cap level for nesting (h2/h3/h4).
        level = max(2, min(4, level))
        cls = "toc-l1" if level == 2 else ""
        link = f'<a href="#{slug}">{escape(text)}</a>'

        if level > current_level:
            # Open nested <ul>s for each step deeper.
            for _ in range(level - current_level):
                parts.append("<ul>")
            current_level = level
            parts.append(f'<li class="{cls}">{link}')
            open_lis += 1
        elif level < current_level:
            # Close open <li> + nested <ul>s back to this level.
            for _ in range(current_level - level):
                parts.append("</li>")
                parts.append("</ul>")
            parts.append("</li>")  # close the previous sibling at this level
            parts.append(f'<li class="{cls}">{link}')
            current_level = level
        else:
            # Same level: close previous sibling, start new one.
            if open_lis > 0:
                parts.append("</li>")
            parts.append(f'<li class="{cls}">{link}')
            open_lis = max(open_lis, 1)

    # Close any remaining open <li> + nested <ul>s.
    while current_level > 2:
        parts.append("</li>")
        parts.append("</ul>")
        current_level -= 1
    parts.append("</li>")
    parts.append("</ul>")
    parts.append("</nav>")
    return "\n".join(parts)


def render(report: Report) -> str:
    """Render a Report to a complete self-contained HTML string."""
    ts = report.timestamp or datetime.now()
    cards_html = "\n".join(
        '<div class="stat-card">'
        f'<div class="stat-label">{escape(c.label)}</div>'
        f'<div class="stat-value">{escape(c.value)}</div>'
        '</div>'
        for c in report.stat_cards
    )

    used_slugs: set[str] = set()
    toc_entries: list[tuple[int, str, str]] = []
    section_chunks: list[str] = []

    for s in report.sections:
        sec_slug = _slugify(s.title, used_slugs)
        toc_entries.append((2, sec_slug, s.title))
        new_body, sub_entries = _inject_ids_and_collect(s.body_html, used_slugs)
        toc_entries.extend(sub_entries)
        section_chunks.append(
            f'<div class="section" id="{sec_slug}">'
            f'<h2 class="section-title">{escape(s.title)}</h2>'
            f'{new_body}'
            '<div class="back-to-toc">'
            '<a href="#contents">↑ Back to contents</a>'
            '</div>'
            '</div>'
        )

    sections_html = "\n".join(section_chunks)
    toc_html = _render_toc(toc_entries)

    return (
        '<!DOCTYPE html>\n<html>\n<head>\n'
        '<meta charset="utf-8">\n'
        f'<title>{escape(report.title)}</title>\n'
        f'<style>{_CSS}</style>\n'
        '</head>\n<body>\n'
        '<div class="container">\n'
        f'<h1>{escape(report.title)}</h1>\n'
        f'<div class="timestamp">Generated on {ts.strftime("%Y-%m-%d %H:%M:%S")}</div>\n'
        f'<div class="summary-grid">{cards_html}</div>\n'
        f'{toc_html}\n'
        f'{sections_html}\n'
        '</div>\n'
        '</body>\n</html>\n'
    )
