from __future__ import annotations

import re
import tempfile
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from xml.etree import ElementTree

from markitdown import MarkItDown

from src.kenyalaw.fetcher import FetchBinaryResult, KenyaLawFetchError
from src.kenyalaw.parser import (
    ParsedCase,
    ParsedSourceLink,
    normalize_case_text,
    parse_case_html,
)
from src.legal_cleaner.cleaner import clean_legal_text


VALID_EXTRACTION = "valid"
REJECTED_SHELL_TEXT = "rejected_shell_text"
SOURCE_MISSING = "source_missing"
SOURCE_EXTRACTION_FAILED = "source_extraction_failed"


@dataclass(frozen=True)
class SourceCandidate:
    url: str
    source_format: str | None = None


@dataclass(frozen=True)
class TextQualityResult:
    status: str
    score: int
    message: str | None = None


@dataclass(frozen=True)
class SourceExtractionResult:
    url: str
    source_format: str
    text: str
    raw_content: bytes
    quality: TextQualityResult


class SourceExtractionFailure(RuntimeError):
    def __init__(
        self,
        *,
        status: str,
        message: str,
        url: str | None = None,
        source_format: str | None = None,
        score: int = 0,
    ):
        super().__init__(message)
        self.status = status
        self.message = message
        self.url = url
        self.source_format = source_format
        self.score = score


def resolve_source_candidates(
    case_url: str, links: tuple[ParsedSourceLink, ...] = ()
) -> list[SourceCandidate]:
    base_url = _without_query_or_fragment(case_url).rstrip("/")
    candidates = [
        SourceCandidate(f"{base_url}/source"),
        SourceCandidate(f"{base_url}/source.pdf", "pdf"),
    ]
    for link in links:
        source_format = _format_from_link(link.url, link.label)
        if source_format:
            candidates.append(SourceCandidate(link.url, source_format))
    return _dedupe_candidates(candidates)


def extract_judgment_source(fetcher, parsed: ParsedCase) -> SourceExtractionResult:
    candidates = resolve_source_candidates(parsed.canonical_url, parsed.source_links)
    if not candidates:
        raise SourceExtractionFailure(
            status=SOURCE_MISSING,
            message="No Kenya Law source document links were found.",
            url=parsed.canonical_url,
        )

    errors: list[str] = []
    fetch_errors: list[KenyaLawFetchError] = []
    rejected: TextQualityResult | None = None
    rejected_url: str | None = None
    rejected_format: str | None = None

    for candidate in candidates:
        try:
            fetched = _fetch_bytes(fetcher, candidate.url)
        except KenyaLawFetchError as exc:
            fetch_errors.append(exc)
            errors.append(f"{candidate.url}: {exc.error_type}")
            continue

        source_format = _detect_source_format(
            fetched.url,
            fetched.content_type,
            fetched.content,
            candidate.source_format,
        )
        try:
            text = extract_source_text(
                fetched.content,
                source_format=source_format,
                source_url=fetched.url,
            )
        except Exception as exc:
            errors.append(f"{fetched.url}: {exc.__class__.__name__}: {exc}")
            continue

        quality = assess_judgment_text_quality(
            text,
            title=parsed.title,
            court=parsed.court,
            citation=parsed.neutral_citation,
        )
        if quality.status == VALID_EXTRACTION:
            return SourceExtractionResult(
                url=fetched.url,
                source_format=source_format,
                text=normalize_case_text(text),
                raw_content=fetched.content,
                quality=quality,
            )
        rejected = quality
        rejected_url = fetched.url
        rejected_format = source_format
        errors.append(f"{fetched.url}: {quality.status}: {quality.message}")

    if fetch_errors and len(fetch_errors) == len(candidates) and all(
        exc.error_type == "http_404" for exc in fetch_errors
    ):
        raise SourceExtractionFailure(
            status=SOURCE_MISSING,
            message="No Kenya Law source document endpoint responded for this judgment.",
            url=parsed.canonical_url,
        )
    if rejected:
        raise SourceExtractionFailure(
            status=REJECTED_SHELL_TEXT,
            message=rejected.message or "Extracted text failed the judgment body quality gate.",
            url=rejected_url,
            source_format=rejected_format,
            score=rejected.score,
        )
    raise SourceExtractionFailure(
        status=SOURCE_EXTRACTION_FAILED,
        message="; ".join(errors) or "Kenya Law source document extraction failed.",
        url=parsed.canonical_url,
    )


def extract_source_text(content: bytes, *, source_format: str, source_url: str) -> str:
    if source_format == "pdf":
        return _extract_pdf(content)
    if source_format == "docx":
        return _extract_docx(content)
    if source_format == "doc":
        return _extract_word_document(content, source_url=source_url)
    if source_format == "rtf":
        return normalize_case_text(clean_legal_text(_strip_rtf(_decode_text(content))))
    decoded = _decode_text(content)
    if "<html" in decoded[:1000].lower() or "<body" in decoded[:1000].lower():
        decoded = parse_case_html(decoded, source_url).text
    return normalize_case_text(clean_legal_text(decoded))


def assess_judgment_text_quality(
    text: str,
    *,
    title: str | None = None,
    court: str | None = None,
    citation: str | None = None,
) -> TextQualityResult:
    normalized = normalize_case_text(clean_legal_text(text))
    compact = re.sub(r"\s+", " ", normalized).strip()
    lowered = compact.lower()
    if len(compact) < 350:
        return TextQualityResult(
            status=REJECTED_SHELL_TEXT,
            score=0,
            message="Extracted text is too short to be a judgment body.",
        )

    shell_hits = sum(lowered.count(term) for term in _SHELL_TERMS)
    numbered_paragraphs = len(
        re.findall(r"(?m)^\s*(?:\[\d+\]|\d+[\.\)]|\(\d+\))\s+\S+", normalized)
    )
    legal_terms = sum(1 for term in _LEGAL_TERMS if term in lowered)

    score = 0
    if len(compact) >= 600:
        score += 15
    if len(compact) >= 1500:
        score += 10
    if re.search(
        r"\b(republic of kenya|in the .*court|environment and land court)\b",
        lowered,
    ):
        score += 22
    if re.search(r"\b(judgment|judgement|ruling|orders?)\b", lowered):
        score += 14
    if numbered_paragraphs >= 2:
        score += 22
    elif numbered_paragraphs == 1:
        score += 8
    if legal_terms >= 4:
        score += 12
    elif legal_terms >= 2:
        score += 6
    if re.search(r"\b(delivered|dated|signed|costs|decree)\b", lowered):
        score += 8
    if _has_title_continuity(lowered, title):
        score += 8
    if citation and citation.lower() in lowered:
        score += 6
    if court and _court_words_match(lowered, court):
        score += 6

    score = max(0, min(100, score - min(35, shell_hits * 5)))
    if shell_hits >= 3 and score < 55:
        return TextQualityResult(
            status=REJECTED_SHELL_TEXT,
            score=score,
            message="Extracted text is dominated by Kenya Law navigation/download shell text.",
        )
    if score < 35:
        return TextQualityResult(
            status=REJECTED_SHELL_TEXT,
            score=score,
            message="Extracted text does not contain enough judgment body signals.",
        )
    return TextQualityResult(status=VALID_EXTRACTION, score=score)


_SHELL_TERMS = (
    "load document",
    "download pdf",
    "download docx",
    "download judgment",
    "kenya law",
    "national council for law reporting",
    "privacy policy",
    "advanced search",
    "judgments",
    "legislation",
    "footer",
)

_LEGAL_TERMS = (
    "plaintiff",
    "defendant",
    "applicant",
    "respondent",
    "court",
    "suit",
    "application",
    "injunction",
    "land",
    "parcel",
    "title",
    "evidence",
    "costs",
    "orders",
)


def _fetch_bytes(fetcher, url: str) -> FetchBinaryResult:
    fetch_bytes = getattr(fetcher, "fetch_bytes", None)
    if fetch_bytes:
        return fetch_bytes(url)
    fetched = fetcher.fetch_text(url)
    return FetchBinaryResult(
        url=fetched.url,
        content=fetched.content.encode("utf-8"),
        content_type=fetched.content_type,
    )


def _extract_pdf(content: bytes) -> str:
    path = _write_temp(content, suffix=".pdf")
    try:
        try:
            from src.legal_cleaner.extractor import extract_text as extract_pdf_text

            text = extract_pdf_text(path)
        except ModuleNotFoundError:
            try:
                text = MarkItDown().convert(path).markdown
            except Exception as exc:
                raise RuntimeError(
                    "PDF extraction dependencies are not installed. Install backend "
                    "requirements, including PyMuPDF and pdfplumber, or install "
                    "markitdown[pdf]."
                ) from exc
        return normalize_case_text(clean_legal_text(text))
    finally:
        path.unlink(missing_ok=True)


def _extract_docx(content: bytes) -> str:
    path = _write_temp(content, suffix=".docx")
    try:
        if not _zip_contains(content, "word/document.xml"):
            return _extract_word_document(content, source_url="")
        try:
            markdown = MarkItDown().convert(path).markdown
            if markdown.strip():
                return normalize_case_text(clean_legal_text(markdown))
        except Exception:
            # MarkItDown covers normal DOCX files; fall back for tiny/generated fixtures.
            pass
        return normalize_case_text(clean_legal_text(_extract_docx_xml(content)))
    finally:
        path.unlink(missing_ok=True)


def _extract_word_document(content: bytes, *, source_url: str) -> str:
    if _looks_like_zip(content):
        return _extract_zip_text(content)
    decoded = _decode_text(content)
    decoded_head = decoded[:1000].lower()
    if content.lstrip().startswith(b"{\\rtf") or decoded.lstrip().startswith("{\\rtf"):
        return normalize_case_text(clean_legal_text(_strip_rtf(decoded)))
    if "<html" in decoded_head or "<body" in decoded_head:
        return normalize_case_text(clean_legal_text(parse_case_html(decoded, source_url).text))
    markitdown_text = _convert_with_markitdown(content, suffix=".doc")
    if markitdown_text:
        return normalize_case_text(clean_legal_text(markitdown_text))
    fallback_text = _extract_binary_word_text(content)
    if fallback_text:
        return normalize_case_text(clean_legal_text(fallback_text))
    raise ValueError("Legacy Word document did not contain extractable text.")


def _extract_docx_xml(content: bytes) -> str:
    with zipfile.ZipFile(BytesIO(content)) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs: list[str] = []
    for paragraph in root.iter(f"{namespace}p"):
        parts = [
            text_node.text or ""
            for text_node in paragraph.iter(f"{namespace}t")
            if text_node.text
        ]
        value = "".join(parts).strip()
        if value:
            paragraphs.append(value)
    return "\n\n".join(paragraphs)


def _extract_zip_text(content: bytes) -> str:
    parts: list[str] = []
    with zipfile.ZipFile(BytesIO(content)) as archive:
        names = archive.namelist()
        if "word/document.xml" in names:
            return _extract_docx_xml(content)
        for name in names:
            lower_name = name.lower()
            if lower_name.endswith((".docx", ".doc", ".rtf", ".html", ".htm", ".txt")):
                nested = archive.read(name)
                nested_format = _detect_source_format(name, "", nested, None)
                parts.append(
                    extract_source_text(
                        nested,
                        source_format=nested_format,
                        source_url=name,
                    )
                )
            elif lower_name.endswith(".xml"):
                parts.append(_extract_generic_xml_text(archive.read(name)))
    text = "\n\n".join(part for part in parts if part.strip())
    if text.strip():
        return normalize_case_text(clean_legal_text(text))
    raise ValueError(f"ZIP source did not contain extractable judgment text: {names[:10]}")


def _extract_generic_xml_text(content: bytes) -> str:
    root = ElementTree.fromstring(content)
    parts = [text.strip() for text in root.itertext() if text and text.strip()]
    return "\n\n".join(parts)


def _convert_with_markitdown(content: bytes, *, suffix: str) -> str | None:
    path = _write_temp(content, suffix=suffix)
    try:
        try:
            markdown = MarkItDown().convert(path).markdown
        except Exception:
            return None
        return markdown.strip() or None
    finally:
        path.unlink(missing_ok=True)


def _write_temp(content: bytes, *, suffix: str) -> Path:
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        handle.write(content)
        return Path(handle.name)
    finally:
        handle.close()


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _detect_source_format(
    url: str,
    content_type: str,
    content: bytes,
    fallback: str | None,
) -> str:
    lower_type = content_type.lower()
    lower_path = urlparse(url).path.lower()
    if (
        content.startswith(b"%PDF")
        or "application/pdf" in lower_type
        or lower_path.endswith(".pdf")
    ):
        return "pdf"
    if content.lstrip().startswith(b"{\\rtf") or lower_path.endswith(".rtf"):
        return "rtf"
    if content.startswith(b"\xd0\xcf\x11\xe0") or lower_path.endswith(".doc"):
        return "doc"
    if (
        _zip_contains(content, "word/document.xml")
        or "wordprocessingml" in lower_type
        or lower_path.endswith(".docx")
    ):
        return "docx"
    if content.startswith(b"PK\x03\x04") or "application/msword" in lower_type:
        return "doc"
    if fallback in {"pdf", "docx", "doc", "rtf"}:
        return fallback
    return "html"


def _format_from_link(url: str, label: str) -> str | None:
    value = f"{url} {label}".lower()
    if ".pdf" in value or "pdf" in label.lower():
        return "pdf"
    if ".docx" in value or "docx" in label.lower() or "word" in label.lower():
        return "docx"
    if ".doc" in value:
        return "doc"
    if "download" in value and "source" in value:
        return "html"
    return None


def _without_query_or_fragment(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query="", fragment=""))


def _dedupe_candidates(candidates: list[SourceCandidate]) -> list[SourceCandidate]:
    seen: set[str] = set()
    unique: list[SourceCandidate] = []
    for candidate in candidates:
        if candidate.url in seen:
            continue
        seen.add(candidate.url)
        unique.append(candidate)
    return unique


def _has_title_continuity(lowered_text: str, title: str | None) -> bool:
    if not title:
        return False
    words = [
        word.lower()
        for word in re.findall(r"[A-Za-z]{4,}", title)
        if word.lower() not in {"judgment", "ruling", "kenya", "case", "klr"}
    ]
    if not words:
        return False
    return sum(1 for word in words[:8] if word in lowered_text) >= min(2, len(words))


def _court_words_match(lowered_text: str, court: str) -> bool:
    words = [
        word.lower()
        for word in re.findall(r"[A-Za-z]{4,}", court)
        if word.lower() not in {"court", "division"}
    ]
    return bool(words) and any(word in lowered_text for word in words)


def _looks_like_zip(content: bytes) -> bool:
    return content.startswith(b"PK\x03\x04")


def _zip_contains(content: bytes, name: str) -> bool:
    if not _looks_like_zip(content):
        return False
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            return name in archive.namelist()
    except zipfile.BadZipFile:
        return False


def _strip_rtf(text: str) -> str:
    text = re.sub(r"\\'[0-9a-fA-F]{2}", " ", text)
    text = re.sub(r"\\[a-zA-Z]+-?\d* ?", " ", text)
    text = text.replace("{", " ").replace("}", " ")
    text = text.replace("\\", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_binary_word_text(content: bytes) -> str | None:
    candidates: list[str] = []
    for encoding in ("utf-16le", "latin-1"):
        decoded = content.decode(encoding, errors="ignore")
        chunks = re.findall(r"[A-Za-z0-9][A-Za-z0-9\s.,;:'\"()\-/&%]{30,}", decoded)
        candidates.extend(chunk.strip() for chunk in chunks)
    seen: set[str] = set()
    useful: list[str] = []
    for chunk in candidates:
        chunk = normalize_case_text(chunk)
        key = chunk[:120]
        if key in seen:
            continue
        seen.add(key)
        lowered = chunk.lower()
        if any(term in lowered for term in _LEGAL_TERMS) or len(chunk) > 120:
            useful.append(chunk)
    return "\n\n".join(useful[:80]).strip() or None
