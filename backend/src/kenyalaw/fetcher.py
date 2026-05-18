import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class KenyaLawFetchError(RuntimeError):
    def __init__(self, url: str, error_type: str, message: str):
        super().__init__(message)
        self.url = url
        self.error_type = error_type


@dataclass(frozen=True)
class FetchResult:
    url: str
    content: str
    content_type: str


@dataclass(frozen=True)
class FetchBinaryResult:
    url: str
    content: bytes
    content_type: str


class KenyaLawFetcher:
    def __init__(self, *, timeout_seconds: int = 20, delay_seconds: float = 1.0):
        self.timeout_seconds = timeout_seconds
        self.delay_seconds = delay_seconds
        self._last_fetch_at = 0.0

    def fetch_text(self, url: str) -> FetchResult:
        fetched = self._fetch(
            url,
            accept="text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
        )
        charset = fetched.get("charset") or "utf-8"
        return FetchResult(
            url=fetched["url"],
            content=fetched["content"].decode(charset, errors="replace"),
            content_type=fetched["content_type"],
        )

    def fetch_bytes(self, url: str) -> FetchBinaryResult:
        fetched = self._fetch(
            url,
            accept=(
                "application/pdf,"
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
                "application/msword,"
                "text/html;q=0.8,text/plain;q=0.8,*/*;q=0.5"
            ),
        )
        return FetchBinaryResult(
            url=fetched["url"],
            content=fetched["content"],
            content_type=fetched["content_type"],
        )

    def _fetch(self, url: str, *, accept: str) -> dict:
        elapsed = time.monotonic() - self._last_fetch_at
        if elapsed < self.delay_seconds:
            time.sleep(self.delay_seconds - elapsed)

        request = Request(
            url,
            headers={
                "User-Agent": "LegalDocs ELC Corpus Bot/1.0 (polite research indexing)",
                "Accept": accept,
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                self._last_fetch_at = time.monotonic()
                raw = response.read()
                content_type = response.headers.get("Content-Type", "")
                charset = response.headers.get_content_charset()
                return {
                    "url": response.geturl(),
                    "content": raw,
                    "content_type": content_type,
                    "charset": charset,
                }
        except HTTPError as exc:
            raise KenyaLawFetchError(url, f"http_{exc.code}", str(exc)) from exc
        except URLError as exc:
            raise KenyaLawFetchError(url, "network_error", str(exc.reason)) from exc
        except TimeoutError as exc:
            raise KenyaLawFetchError(url, "timeout", "Timed out fetching Kenya Law") from exc
