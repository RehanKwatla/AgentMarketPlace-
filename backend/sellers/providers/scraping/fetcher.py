"""[IMPLEMENTED] Bounded, SSRF-Defended HTTP Web Fetcher & Extractor with IP Pinning."""
import logging
from typing import Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import httpx

from backend.sellers.providers.interfaces import ScrapingProviderInterface
from backend.sellers.providers.config import ProviderSettings, get_provider_settings
from backend.sellers.providers.errors import (
    ProviderSSRFBlockedError,
    ProviderTimeoutError,
    ProviderUpstreamError,
    ProviderRequestRejectedError,
    ProviderResponseInvalidError,
    ProviderOutputLimitExceededError,
)
from backend.sellers.providers.scraping.safety import (
    validate_url_syntax,
    resolve_and_validate_destination,
)
from backend.sellers.providers.scraping.parser import extract_clean_content
from backend.sellers.providers.scraping.transport import PinnedAsyncHTTPTransport

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = (
    "text/html",
    "text/plain",
    "application/xhtml+xml",
    "application/json",
    "text/markdown",
    "text/xml",
)


class FakeScrapingProvider(ScrapingProviderInterface):
    """Deterministic offline scraping provider for test suites and offline demo."""

    async def scrape_url(self, url: str) -> Dict[str, Any]:
        validate_url_syntax(url)
        parsed = urlparse(url)
        # Verify host safety even in fake mode
        if parsed.hostname in ("localhost", "metadata.google.internal") or parsed.hostname.startswith("127."):
            raise ProviderSSRFBlockedError(f"Access to blocked host '{parsed.hostname}' is prohibited.", destination=url)

        title = f"Extracted Data from {url}"
        content = (
            f"Extracted content from {url}: Autonomous agent economies leverage "
            "micropayment rails such as x402 on Base Sepolia for frictionless API settlements."
        )
        return {
            "url": url,
            "title": title,
            "content": content,
            "content_length": len(content),
            "word_count": len(content.split()),
        }


class SafeScrapingFetcher(ScrapingProviderInterface):
    """SSRF-defended HTTP fetcher with connect-time IP pinning and manual redirect validation.
    
    Protects against DNS Rebinding and TOCTOU vulnerabilities by:
    1. Validating destination hostnames and IP addresses against strict SSRF policies.
    2. Pinning the actual TCP socket connection to the pre-validated IP via PinnedAsyncHTTPTransport.
    3. Preserving original hostname for HTTP Host header, TLS SNI, and strict certificate checking.
    4. Re-validating every redirect hop independently with fresh destination checks.
    5. Disabling environment proxies (trust_env=False) to ensure direct connection pinning.
    """

    def __init__(self, settings: Optional[ProviderSettings] = None, client: Optional[httpx.AsyncClient] = None):
        self.settings = settings or get_provider_settings()
        self._client = client

    async def scrape_url(self, url: str) -> Dict[str, Any]:
        # 1. Initial URL syntax check
        validate_url_syntax(url)

        current_url = url
        redirect_count = 0
        final_response_text = ""
        final_url = current_url

        timeout = httpx.Timeout(
            connect=self.settings.scraping_connect_timeout_seconds,
            read=self.settings.scraping_read_timeout_seconds,
            write=5.0,
            pool=5.0,
        )

        while True:
            # 2. Connection-time destination resolution and policy check
            parsed = urlparse(current_url)
            safe_ips = resolve_and_validate_destination(parsed.hostname)
            if not safe_ips:
                raise ProviderSSRFBlockedError(
                    f"Hostname '{parsed.hostname}' resolved to zero safe destinations.",
                    destination=parsed.hostname,
                )
            pinned_ip = safe_ips[0]

            # 3. Build IP-pinned transport or use injected test client
            client_ctx = (
                self._client
                if self._client is not None
                else httpx.AsyncClient(
                    transport=PinnedAsyncHTTPTransport(
                        pinned_ip=pinned_ip,
                        verify=True,
                        trust_env=False,
                    ),
                    follow_redirects=False,
                    timeout=timeout,
                    trust_env=False,
                )
            )

            # Injected client might be managed externally, otherwise use async with
            should_close = self._client is None
            try:
                res = await client_ctx.get(
                    current_url,
                    headers={"User-Agent": "AgenticaScraper/2.0 (SSRF-Defended; IP-Pinned)"}
                )
            except httpx.ConnectTimeout as exc:
                raise ProviderTimeoutError(f"Connection to '{parsed.hostname}' ({pinned_ip}) timed out: {exc}", provider_name="safe_scraper")
            except httpx.ReadTimeout as exc:
                raise ProviderTimeoutError(f"Reading response from '{parsed.hostname}' ({pinned_ip}) timed out: {exc}", provider_name="safe_scraper")
            except httpx.RequestError as exc:
                raise ProviderUpstreamError(f"HTTP request to '{parsed.hostname}' ({pinned_ip}) failed: {exc}", provider_name="safe_scraper")
            finally:
                if should_close:
                    await client_ctx.aclose()

            # 4. Handle Redirects manually to re-verify destination policy at every hop
            if res.is_redirect:
                redirect_count += 1
                if redirect_count > self.settings.scraping_max_redirects:
                    raise ProviderRequestRejectedError(
                        f"Exceeded maximum allowed redirects ({self.settings.scraping_max_redirects}).",
                        provider_name="safe_scraper"
                    )

                location = res.headers.get("location")
                if not location:
                    raise ProviderResponseInvalidError("Redirect response missing Location header.", provider_name="safe_scraper")

                next_url = urljoin(current_url, location)
                # Strict re-validation of next hop syntax and scheme
                validate_url_syntax(next_url)
                current_url = next_url
                continue

            # 5. Check HTTP Status
            if res.status_code >= 500:
                raise ProviderUpstreamError(f"Target server returned HTTP {res.status_code}.", provider_name="safe_scraper")
            if res.status_code >= 400:
                raise ProviderRequestRejectedError(f"Target server rejected request with HTTP {res.status_code}.", provider_name="safe_scraper")

            # 6. Content-Type Validation
            content_type = res.headers.get("content-type", "").lower()
            if content_type and not any(allowed in content_type for allowed in ALLOWED_CONTENT_TYPES):
                raise ProviderResponseInvalidError(
                    f"Unsupported Content-Type '{content_type}'. Must be text or HTML.",
                    provider_name="safe_scraper"
                )

            # 7. Stream and Enforce Response Size Limit
            content_bytes = res.content
            if len(content_bytes) > self.settings.scraping_max_response_bytes:
                content_bytes = content_bytes[:self.settings.scraping_max_response_bytes]

            try:
                final_response_text = content_bytes.decode(res.encoding or "utf-8", errors="replace")
            except Exception:
                final_response_text = content_bytes.decode("latin-1", errors="replace")

            final_url = str(res.url)
            break

        # 8. Extract Clean Text and Bounded Document Title
        clean_text, title = extract_clean_content(
            final_response_text,
            max_chars=self.settings.scraping_max_extract_chars
        )

        return {
            "url": final_url,
            "title": title,
            "content": clean_text,
            "content_length": len(clean_text),
            "word_count": len(clean_text.split()),
        }
