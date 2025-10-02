"""File-focused daily digest runner.

Collects papers using the daily_digest module and saves both markdown and HTML copies
without sending email. Designed for use in the cron-based Docker image.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from daily_digest import (
    PaperCollector,
    format_papers_simple,
    format_papers_with_claude,
    markdown_to_html,
    save_to_file,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def save_html(content: str, markdown_path: Path) -> None:
    html = markdown_to_html(content)
    if html is None:
        logger.warning("Skipping HTML export due to markdown conversion error")
        return

    html_path = markdown_path.with_suffix('.html')
    html_path.write_text(html, encoding='utf-8')
    logger.info("Saved HTML digest to %s", html_path)


def run_file_only_digest() -> None:
    today = date.today()
    today_display = today.strftime("%B %d, %Y")

    collector = PaperCollector()
    papers_by_area = collector.collect()

    total_papers = sum(len(papers) for papers in papers_by_area.values())
    if total_papers == 0:
        logger.warning("No recent papers found; skipping file export")
        return

    content = format_papers_with_claude(papers_by_area, today_display)
    if not content:
        content = format_papers_simple(papers_by_area, today_display)

    markdown_path = save_to_file(content, today)
    save_html(content, markdown_path)


if __name__ == "__main__":
    run_file_only_digest()
