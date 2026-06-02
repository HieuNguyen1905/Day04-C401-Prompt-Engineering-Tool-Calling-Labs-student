import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from typing import Any, Dict, List, Union
from urllib.parse import urljoin, urlparse


DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_USER_AGENT = "ResearchAgent-fetch_rss/1.0"
MAX_ITEMS = 50


class _FeedLinkParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.candidates: List[tuple[int, str]] = []

    def handle_starttag(self, tag: str, attrs: List[tuple[str, Union[str, None]]]) -> None:
        attr_map = {name.lower(): value or "" for name, value in attrs}
        href = attr_map.get("href", "").strip()
        if not href:
            return

        href_lower = href.lower()
        rel = attr_map.get("rel", "").lower()
        type_ = attr_map.get("type", "").lower()
        title = attr_map.get("title", "").lower()
        text = " ".join([href_lower, rel, type_, title])

        if tag == "link" and ("rss" in type_ or "atom" in type_ or "alternate" in rel):
            priority = 5
        elif ".rss" in href_lower or href_lower.endswith(("/feed", "/rss.xml", "/atom.xml")):
            priority = 20
        else:
            return

        if "tin-moi-nhat" in text or "latest" in text:
            priority = 1
        elif "tin-noi-bat" in text or "nổi bật" in text or "noi bat" in text:
            priority = 2
        elif "frontpage" in text or "feed" in text:
            priority = min(priority, 10)

        self.candidates.append((priority, urljoin(self.base_url, href)))


def _local_name(tag: str) -> str:
    """Return an XML tag name without its optional namespace."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _find_child(element: ET.Element, name: str) -> Union[ET.Element, None]:
    for child in element:
        if _local_name(child.tag) == name:
            return child
    return None


def _find_children(element: ET.Element, name: str) -> List[ET.Element]:
    return [child for child in element if _local_name(child.tag) == name]


def _text_from_child(element: ET.Element, name: str) -> str:
    child = _find_child(element, name)
    if child is None or child.text is None:
        return ""
    return child.text.strip()


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


def _request_content(url: str) -> tuple[bytes, str, str]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, text/html;q=0.5, */*;q=0.1",
            "User-Agent": DEFAULT_USER_AGENT,
        },
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
        status_code = getattr(response, "status", None)
        if status_code is not None and status_code >= 400:
            raise urllib.error.HTTPError(
                url,
                status_code,
                f"HTTP {status_code}",
                response.headers,
                None,
            )
        content_type = response.headers.get("content-type", "")
        final_url = response.geturl()
        return response.read(), content_type, final_url


def _looks_like_html(content: bytes, content_type: str) -> bool:
    if "html" in content_type.lower():
        return True
    prefix = content.lstrip()[:100].lower()
    return prefix.startswith(b"<!doctype html") or prefix.startswith(b"<html")


def _discover_feed_url(content: bytes, base_url: str) -> str:
    html = content.decode("utf-8", errors="replace")
    parser = _FeedLinkParser(base_url)
    parser.feed(html)
    if not parser.candidates:
        return ""
    return sorted(parser.candidates, key=lambda item: item[0])[0][1]


def fetch_rss(feed_url: str, limit: int = 5) -> Union[List[Dict[str, Any]], str]:
    """
    Fetches latest articles from an RSS feed URL.

    Args:
        feed_url (str): The valid URL of the RSS feed.
        limit (int): Maximum number of items to return. Defaults to 5.

    Returns:
        Union[List[Dict[str, Any]], str]: A list of article metadata dictionaries, or an error string.
    """
    if not isinstance(feed_url, str) or not feed_url.strip():
        return "Error fetching RSS feed: feed_url must be a non-empty string."

    try:
        item_limit = int(limit)
    except (TypeError, ValueError):
        return "Error fetching RSS feed: limit must be an integer."

    if item_limit < 1:
        return "Error fetching RSS feed: limit must be at least 1."

    item_limit = min(item_limit, MAX_ITEMS)
    feed_url = feed_url.strip()

    try:
        xml_content, content_type, final_url = _request_content(feed_url)
        if _looks_like_html(xml_content, content_type):
            discovered_url = _discover_feed_url(xml_content, final_url)
            if not discovered_url:
                return f"Error fetching RSS feed: {feed_url} returned HTML and no RSS feed link was found."
            xml_content, _, _ = _request_content(discovered_url)

        root = ET.fromstring(xml_content)
        channel = _find_child(root, "channel")
        if channel is None:
            return "Error parsing RSS feed: no <channel> element found."

        items = _find_children(channel, "item")
        if not items:
            return "No RSS items found in the feed."

        articles: List[Dict[str, Any]] = []
        for item in items[:item_limit]:
            link = _text_from_child(item, "link")
            articles.append(
                {
                    "title": _text_from_child(item, "title"),
                    "link": link,
                    "url": link,
                    "source": _domain(link),
                    "pubDate": _text_from_child(item, "pubDate"),
                }
            )

        return articles

    except urllib.error.HTTPError as exc:
        return f"Error fetching RSS feed: HTTP {exc.code} {exc.reason} for {feed_url}."
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        return f"Error fetching RSS feed: {reason}."
    except ET.ParseError as exc:
        return f"Error parsing RSS feed XML: {exc}."
    except TimeoutError:
        return f"Error fetching RSS feed: request timed out after {DEFAULT_TIMEOUT_SECONDS} seconds."
    except Exception as exc:
        return f"Unexpected error fetching RSS feed: {type(exc).__name__}: {exc}."
