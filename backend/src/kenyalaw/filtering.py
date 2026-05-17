import re


ELC_COURT_PATTERNS = (
    "environment and land",
    "environment & land",
    "elc",
)

ELC_TOPIC_PATTERNS = (
    "adverse possession",
    "injunction",
    "temporary injunction",
    "interlocutory injunction",
    "land registration",
    "land act",
    "limitation of actions",
    "eviction",
    "trespass",
    "specific performance",
    "title deed",
    "green card",
    "land parcel",
    "environment and land",
)

EXCLUDED_TOPIC_PATTERNS = (
    "criminal",
    "murder",
    "robbery",
    "defilement",
    "employment and labour",
    "succession",
    "probate",
    "matrimonial",
    "tax appeal",
)


def normalize_space(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def is_elc_relevant(*, title: str, court: str | None, text: str = "") -> bool:
    haystack = " ".join([title or "", court or "", text or ""]).lower()
    if any(pattern in haystack for pattern in EXCLUDED_TOPIC_PATTERNS):
        return False
    if any(pattern in (court or "").lower() for pattern in ELC_COURT_PATTERNS):
        return True
    return any(pattern in haystack for pattern in ELC_TOPIC_PATTERNS)


def topic_tags_for(*, title: str, court: str | None, text: str = "") -> list[str]:
    haystack = " ".join([title or "", court or "", text or ""]).lower()
    tags = [pattern for pattern in ELC_TOPIC_PATTERNS if pattern in haystack]
    if any(pattern in (court or "").lower() for pattern in ELC_COURT_PATTERNS):
        tags.insert(0, "environment and land court")
    return sorted(set(tags))

