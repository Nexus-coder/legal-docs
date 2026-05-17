import hashlib
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin

from src.kenyalaw.filtering import normalize_space, topic_tags_for


@dataclass(frozen=True)
class ParsedCase:
    canonical_url: str
    title: str
    neutral_citation: str | None
    court: str | None
    judgment_date: str | None
    text: str
    source_format: str
    raw_hash: str
    normalized_hash: str
    topic_tags: list[str]


class _JudgmentHtmlParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []
        self._parts: list[str] = []
        self._title_parts: list[str] = []
        self._in_title = False
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        if tag == "a":
            href = attrs_dict.get("href")
            if href:
                self.links.append(href)
        if tag in {"p", "br", "div", "tr", "h1", "h2", "h3", "li"}:
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False
        if tag in {"p", "div", "tr", "h1", "h2", "h3", "li"}:
            self._parts.append("\n")

    def handle_data(self, data):
        if self._skip_depth:
            return
        if self._in_title:
            self._title_parts.append(data)
        self._parts.append(data)

    @property
    def title(self) -> str:
        return normalize_space(" ".join(self._title_parts))

    @property
    def text(self) -> str:
        lines = [normalize_space(part) for part in "\n".join(self._parts).splitlines()]
        return "\n".join(line for line in lines if line)


def parse_listing_links(html: str, base_url: str) -> list[str]:
    parser = _JudgmentHtmlParser()
    parser.feed(html)
    links = []
    for href in parser.links:
        absolute = urljoin(base_url, href)
        if "/akn/ke/judgment/" in absolute or "/caselaw/cases/view/" in absolute:
            links.append(absolute.split("#", 1)[0])
    return sorted(set(links))


def parse_case_html(html: str, url: str) -> ParsedCase:
    parser = _JudgmentHtmlParser()
    parser.feed(html)
    text = parser.text
    title = _extract_title(parser.title, text)
    court = _extract_labeled_value(text, ("Court", "County", "Court Division"))
    citation = _extract_neutral_citation(title) or _extract_neutral_citation(text)
    date = _extract_date(text)
    normalized_text = normalize_case_text(text)
    raw_hash = hashlib.sha256(html.encode("utf-8", errors="ignore")).hexdigest()
    normalized_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
    return ParsedCase(
        canonical_url=url,
        title=title,
        neutral_citation=citation,
        court=court,
        judgment_date=date,
        text=normalized_text,
        source_format="html",
        raw_hash=raw_hash,
        normalized_hash=normalized_hash,
        topic_tags=topic_tags_for(title=title, court=court, text=normalized_text[:5000]),
    )


def normalize_case_text(text: str) -> str:
    text = re.sub(r"(?i)Kenya Law Reports?|National Council for Law Reporting", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _extract_title(page_title: str, text: str) -> str:
    if page_title and "kenya law" not in page_title.lower():
        return page_title[:500]
    for line in re.split(r"[\n\r]+", text):
        line = normalize_space(line)
        if re.search(r"\b(v|vs|versus)\b", line, flags=re.IGNORECASE):
            return line[:500]
    return normalize_space(text[:200]) or "Untitled Kenya Law judgment"


def _extract_neutral_citation(value: str) -> str | None:
    match = re.search(r"\[\d{4}\]\s*[A-Z]{2,}[A-Z0-9\s]*\d*", value or "")
    return normalize_space(match.group(0)) if match else None


def _extract_date(text: str) -> str | None:
    match = re.search(
        r"\b(\d{1,2}(?:st|nd|rd|th)?\s+"
        r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+\d{4})\b",
        text,
        flags=re.IGNORECASE,
    )
    return normalize_space(match.group(1)) if match else None


def _extract_labeled_value(text: str, labels: tuple[str, ...]) -> str | None:
    for label in labels:
        match = re.search(rf"{label}\s*[:\-]\s*([^\n\r]+)", text, flags=re.IGNORECASE)
        if match:
            return normalize_space(match.group(1))[:180]
    return None
