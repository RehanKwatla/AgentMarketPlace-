"""[IMPLEMENTED] Safe HTML Text & Metadata Extractor."""
import re
from html.parser import HTMLParser
from typing import Tuple


class CleanTextExtractor(HTMLParser):
    """Safe streaming HTML-to-text converter that ignores script and style tags."""

    def __init__(self):
        super().__init__()
        self.reset()
        self._pieces = []
        self._in_script_or_style = False
        self._title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        if t in ("script", "style", "noscript"):
            self._in_script_or_style = True
        elif t == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        t = tag.lower()
        if t in ("script", "style", "noscript"):
            self._in_script_or_style = False
        elif t == "title":
            self._in_title = False
        elif t in ("p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"):
            self._pieces.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self._title += data
        elif not self._in_script_or_style:
            self._pieces.append(data)

    def get_clean_text(self) -> Tuple[str, str]:
        raw_text = "".join(self._pieces)
        # Normalize excessive whitespace
        clean_lines = [re.sub(r"[ \t]+", " ", line).strip() for line in raw_text.splitlines()]
        clean_text = "\n".join([line for line in clean_lines if line])
        title = self._title.strip() or "Untitled Document"
        return clean_text, title


def extract_clean_content(raw_html: str, max_chars: int = 50_000) -> Tuple[str, str]:
    """Extract clean text and document title from raw HTML string, bounded by max_chars.
    
    Returns:
        (extracted_text, document_title)
    """
    if not raw_html or not raw_html.strip():
        return "", "Empty Document"

    parser = CleanTextExtractor()
    try:
        parser.feed(raw_html)
        text, title = parser.get_clean_text()
    except Exception:
        # Fallback to simple tag stripping
        text = re.sub(r"<[^>]+>", " ", raw_html)
        text = re.sub(r"\s+", " ", text).strip()
        title = "Extracted Document"

    if len(text) > max_chars:
        text = text[:max_chars]

    return text, title
