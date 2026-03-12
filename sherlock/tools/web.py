"""Web tools — search and scrape with caching."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from sherlock.config import settings


async def search_web(query: str, max_results: int = 10) -> list[dict[str, str]]:
    """Search the web using a search API.

    This is a stub that uses DuckDuckGo HTML search as a free fallback.
    Replace with SerpAPI, Brave Search API, or similar for production use.
    """
    cache_key = _cache_key(f"search:{query}")
    cached = _read_cache(cache_key)
    if cached:
        return cached

    results: list[dict[str, str]] = []

    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            response = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": "Sherlock-Holmes-AI/0.1 (research agent)"},
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            for result in soup.select(".result")[:max_results]:
                title_el = result.select_one(".result__a")
                snippet_el = result.select_one(".result__snippet")
                if title_el:
                    results.append(
                        {
                            "title": title_el.get_text(strip=True),
                            "url": title_el.get("href", ""),
                            "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                        }
                    )
    except Exception:
        pass  # Fail gracefully

    _write_cache(cache_key, results)
    return results


async def scrape_url(url: str, max_length: int = 5000) -> str:
    """Scrape a URL and return cleaned text content."""
    cache_key = _cache_key(f"scrape:{url}")
    cached = _read_cache(cache_key)
    if cached:
        return cached

    text = ""
    try:
        async with httpx.AsyncClient(
            timeout=settings.request_timeout, follow_redirects=True
        ) as client:
            response = await client.get(
                url,
                headers={"User-Agent": "Sherlock-Holmes-AI/0.1 (research agent)"},
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove script and style elements
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            text = soup.get_text(separator="\n", strip=True)[:max_length]
    except Exception:
        pass

    _write_cache(cache_key, text)
    return text


# --- Simple file-based cache ---


def _cache_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _cache_path(key: str) -> Path:
    settings.ensure_dirs()
    return settings.cache_dir / f"{key}.json"


def _read_cache(key: str) -> str | list | dict | None:
    path = _cache_path(key)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return None
    return None


def _write_cache(key: str, data: str | list | dict) -> None:
    path = _cache_path(key)
    try:
        path.write_text(json.dumps(data))
    except Exception:
        pass
