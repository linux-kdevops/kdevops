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
    sections_html = "\n".join(
        '<div class="section">'
        f'<h2 class="section-title">{escape(s.title)}</h2>'
        f'{s.body_html}'
        '</div>'
        for s in report.sections
    )

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
        f'{sections_html}\n'
        '</div>\n'
        '</body>\n</html>\n'
    )
