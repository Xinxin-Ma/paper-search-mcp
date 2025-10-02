"""Daily Research Paper Automation Script.

Collects recent papers from configured academic sources, formats results with Claude
if available, saves a markdown backup, and emails the digest.
"""

from __future__ import annotations

import os
import logging
import smtplib
from collections import OrderedDict
from datetime import date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import anthropic
import markdown

from paper_search_mcp.academic_platforms.arxiv import ArxivSearcher
from paper_search_mcp.academic_platforms.semantic import SemanticSearcher
from paper_search_mcp.academic_platforms.pubmed import PubMedSearcher
from paper_search_mcp.paper import Paper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment configuration
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")
CLAUDE_MAX_TOKENS = int(os.environ.get("CLAUDE_MAX_TOKENS", "8000"))

EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECIPIENT = os.environ.get("EMAIL_RECIPIENT")
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


RESEARCH_CATEGORIES = OrderedDict(
    {
        "AI & Machine Learning": {
            "queries": [
                "artificial intelligence latest",
                "machine learning new methods",
                "deep learning advances",
            ],
            "include_pubmed": False,
        },
        "Large Language Models (LLMs)": {
            "queries": [
                "large language models",
                "LLM applications",
                "transformer models",
            ],
            "include_pubmed": False,
        },
        "Recommendation Systems & Reinforcement Learning": {
            "queries": [
                "recommendation systems",
                "recommender systems",
                "reinforcement learning",
            ],
            "include_pubmed": False,
        },
        "Multimodal Models": {
            "queries": [
                "multimodal learning",
                "vision language models",
                "cross-modal",
            ],
            "include_pubmed": False,
        },
        "Human-Computer Interaction (HCI)": {
            "queries": [
                "human computer interaction",
                "user interface design",
                "usability research",
            ],
            "include_pubmed": True,
        },
        "IO Psychology & Decision Making": {
            "queries": [
                "industrial organizational psychology",
                "workplace psychology",
                "organizational behavior",
            ],
            "include_pubmed": True,
        },
    }
)


class PaperCollector:
    """Use the project searchers to gather recent papers for each research area."""

    def __init__(self) -> None:
        self.arxiv_searcher = ArxivSearcher()
        self.semantic_searcher = SemanticSearcher()
        self.pubmed_searcher = PubMedSearcher()

    def collect(self) -> Dict[str, List[Dict[str, str]]]:
        papers_by_area: Dict[str, List[Dict[str, str]]] = {}

        for area, config in RESEARCH_CATEGORIES.items():
            logger.info("Searching area: %s", area)
            area_papers: List[Paper] = []

            for query in config["queries"]:
                area_papers.extend(self._search_arxiv(query, limit=5))

                # Semantic Scholar as a secondary source if we need more
                if len(area_papers) < 5:
                    area_papers.extend(self._search_semantic(query, limit=3))

            if config.get("include_pubmed") and len(area_papers) < 5:
                pubmed_query = f"{area.lower()}" if "psychology" in area.lower() else "human computer interaction"
                area_papers.extend(self._search_pubmed(pubmed_query, limit=3))

            normalized = self._prepare_area(area_papers)
            papers_by_area[area] = normalized
            logger.info("Collected %d papers for %s", len(normalized), area)

        return papers_by_area

    def _search_arxiv(self, query: str, limit: int) -> List[Paper]:
        try:
            return self.arxiv_searcher.search(query, max_results=limit)
        except Exception as err:  # pylint: disable=broad-except
            logger.error("ArXiv search failed for query '%s': %s", query, err)
            return []

    def _search_semantic(self, query: str, limit: int) -> List[Paper]:
        try:
            return self.semantic_searcher.search(query, max_results=limit)
        except Exception as err:  # pylint: disable=broad-except
            logger.error("Semantic Scholar search failed for query '%s': %s", query, err)
            return []

    def _search_pubmed(self, query: str, limit: int) -> List[Paper]:
        try:
            return self.pubmed_searcher.search(query, max_results=limit)
        except Exception as err:  # pylint: disable=broad-except
            logger.error("PubMed search failed for query '%s': %s", query, err)
            return []

    def _prepare_area(self, papers: Iterable[Paper]) -> List[Dict[str, str]]:
        unique: Dict[str, Dict[str, str]] = {}
        for paper in papers:
            if not self._is_recent(paper):
                continue

            title_key = "".join(paper.title.lower().split())
            if title_key in unique:
                continue

            unique[title_key] = self._paper_to_dict(paper)

            if len(unique) >= 8:
                break

        return list(unique.values())

    @staticmethod
    def _is_recent(paper: Paper, days: int = 3) -> bool:
        try:
            published = paper.published_date.date() if paper.published_date else None
        except Exception:  # pylint: disable=broad-except
            return False

        if not published:
            return False

        cutoff = date.today() - timedelta(days=days)
        return published >= cutoff

    @staticmethod
    def _paper_to_dict(paper: Paper) -> Dict[str, str]:
        authors = paper.authors[:5]
        authors_str = ", ".join(authors)
        if len(paper.authors) > 5:
            authors_str += " et al."

        try:
            published = paper.published_date.strftime("%Y-%m-%d") if paper.published_date else "Unknown"
        except Exception:  # pylint: disable=broad-except
            published = "Unknown"

        return {
            "title": paper.title.strip(),
            "authors": authors_str,
            "abstract": (paper.abstract or "No abstract available").strip(),
            "published": published,
            "url": paper.url,
            "pdf_url": paper.pdf_url,
            "doi": paper.doi,
            "source": paper.source.upper() if paper.source else "",
        }


def format_papers_with_claude(papers_by_area: Dict[str, List[Dict[str, str]]], today_display: str) -> str:
    """Ask Claude to prepare the final markdown document."""
    if not ANTHROPIC_API_KEY:
        return format_papers_simple(papers_by_area, today_display)

    summary_payload = _build_papers_summary(papers_by_area, today_display)
    prompt = (
        f"Today's date is {today_display}.\n\n"
        "You are helping compile a daily digest of research papers. "
        "Using the structured data provided, produce a polished markdown report that:"
        "\n1. Groups papers by the given categories."
        "\n2. Includes full abstracts, DOI (if available), and links."
        "\n3. Adds a 2-3 sentence impact and innovation analysis for each paper."
        "\n4. Concludes with 3-5 bullet points summarising key trends."
        "\n\nHere is the data:\n\n"
        f"{summary_payload}\n\nFormat the response in clean markdown suitable for Notion."
    )

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        parts: List[str] = []
        for block in response.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
            elif isinstance(block, dict) and "text" in block:
                parts.append(block["text"])
        formatted = "".join(parts).strip()
        return formatted or format_papers_simple(papers_by_area, today_display)
    except Exception as err:  # pylint: disable=broad-except
        logger.error("Error formatting with Claude: %s", err)
        return format_papers_simple(papers_by_area, today_display)


def _build_papers_summary(papers_by_area: Dict[str, List[Dict[str, str]]], today_display: str) -> str:
    lines: List[str] = [f"# Research Papers collected on {today_display}"]
    for area, papers in papers_by_area.items():
        if not papers:
            continue
        lines.append(f"\n## {area}")
        for idx, paper in enumerate(papers, 1):
            lines.append(f"\n### Paper {idx}")
            lines.append(f"Title: {paper['title']}")
            lines.append(f"Authors: {paper['authors']}")
            lines.append(f"Published: {paper['published']}")
            if paper.get('doi'):
                lines.append(f"DOI: {paper['doi']}")
            lines.append(f"Source: {paper['source']}")
            lines.append(f"URL: {paper['url']}")
            if paper.get('pdf_url'):
                lines.append(f"PDF: {paper['pdf_url']}")
            lines.append("Abstract: " + paper['abstract'])
    return "\n".join(lines)


def format_papers_simple(papers_by_area: Dict[str, List[Dict[str, str]]], today_display: str) -> str:
    lines = [f"# Latest Research Papers - {today_display}\n"]
    total_papers = 0

    for area, papers in papers_by_area.items():
        if not papers:
            continue
        lines.append(f"## {area}\n")
        for paper in papers:
            total_papers += 1
            lines.append(f"### {paper['title']}")
            lines.append(f"**Authors:** {paper['authors']}")
            lines.append(f"**Published:** {paper['published']} | **Source:** {paper['source']}")
            lines.append(f"**URL:** {paper['url']}")
            if paper.get('pdf_url'):
                lines.append(f"**PDF:** {paper['pdf_url']}")
            if paper.get('doi'):
                lines.append(f"**DOI:** {paper['doi']}")
            lines.append("**Abstract:**")
            lines.append(paper['abstract'])
            lines.append("\n---\n")

    lines.append("\n## Summary\n")
    lines.append(f"Total papers summarised: {total_papers}")
    return "\n".join(lines)


def markdown_to_html(markdown_content: str) -> Optional[str]:
    try:
        html = markdown.markdown(markdown_content, extensions=["extra", "codehilite", "tables"])
    except Exception as err:  # pylint: disable=broad-except
        logger.warning("Markdown conversion failed: %s", err)
        return None

    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 8px;
        }}
        h3 {{
            color: #555;
            margin-top: 20px;
        }}
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        code {{
            background-color: #f8f9fa;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
        strong {{
            color: #2c3e50;
        }}
        hr {{
            border: none;
            border-top: 1px solid #ecf0f1;
            margin: 30px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        {html}
    </div>
</body>
</html>
"""


def save_to_file(content: str, today: date) -> Path:
    filename = OUTPUT_DIR / f"papers_{today.strftime('%Y%m%d')}.md"
    filename.write_text(content, encoding="utf-8")
    logger.info("Saved digest to %s", filename)
    return filename


def send_email(subject: str, content: str, content_html: Optional[str] = None) -> bool:
    if not all([EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENT]):
        logger.warning("Email configuration incomplete; skipping send")
        return False

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECIPIENT

    text_part = MIMEText(content, 'plain', 'utf-8')
    msg.attach(text_part)

    if content_html:
        html_part = MIMEText(content_html, 'html', 'utf-8')
        msg.attach(html_part)

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        logger.info("Email sent to %s", EMAIL_RECIPIENT)
        return True
    except Exception as err:  # pylint: disable=broad-except
        logger.error("Error sending email: %s", err)
        return False


def run_daily_digest() -> None:
    print("🚀 Starting Daily Research Paper Automation")
    print("=" * 60)

    today = date.today()
    today_display = today.strftime("%B %d, %Y")
    print(f"📅 Date: {today_display}")

    collector = PaperCollector()
    print("\n📚 Collecting papers from sources...")
    papers_by_area = collector.collect()

    total_papers = sum(len(papers) for papers in papers_by_area.values())
    print(f"\n✅ Found {total_papers} papers across {len(papers_by_area)} categories")

    if total_papers == 0:
        print("⚠️  No recent papers found. Exiting.")
        return

    print("\n🤖 Formatting papers with Claude...")
    formatted = format_papers_with_claude(papers_by_area, today_display)
    if not formatted:
        print("❌ Failed to format papers")
        return

    print(f"✅ Formatted content length: {len(formatted)} characters")

    backup_path = save_to_file(formatted, today)
    print(f"📄 Markdown digest saved: {backup_path}")

    print("\n📧 Sending email...")
    subject = f"Latest Research Papers - {today_display} ({total_papers} papers)"
    html_content = markdown_to_html(formatted)
    email_sent = send_email(subject, formatted, html_content)

    if email_sent:
        print("✅ Email sent successfully!")
    else:
        print("⚠️  Email sending failed")

    print("\n" + "=" * 60)
    print("✨ Daily automation completed!")


if __name__ == "__main__":
    run_daily_digest()
