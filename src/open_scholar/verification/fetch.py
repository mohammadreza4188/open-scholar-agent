"""Polite, safe page retrieval.

* http/https only; refuses private, loopback and link-local addresses (SSRF guard), re-checked on every redirect
* obeys robots.txt (unreachable or 5xx robots => treated as disallowed)
* no CAPTCHA/login bypass; size and content-type limits
"""
from __future__ import annotations

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Awaitable, Callable
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

USER_AGENT = "OpenScholarAgent/0.1 (open-source research assistant)"
MAX_BYTES = 1_500_000
MAX_REDIRECTS = 3
_SKIP = {"script", "style", "noscript", "template", "svg"}
_BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "table", "ul", "ol"}


class FetchError(Exception):
    pass


@dataclass
class FetchedPage:
    url: str
    text: str


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP:
            self._skip += 1
        elif tag == "title":
            self._in_title = True
        if tag in _BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in _SKIP and self._skip:
            self._skip -= 1
        elif tag == "title":
            self._in_title = False
        if tag in _BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    p = _TextExtractor()
    p.feed(html)
    lines = (" ".join(line.split()) for line in "".join(p.parts).split("\n"))
    return "\n".join(l for l in lines if l)


async def default_resolver(host: str) -> list[str]:
    infos = await asyncio.to_thread(socket.getaddrinfo, host, None)
    return [i[4][0] for i in infos]


def _public(ip: str) -> bool:
    a = ipaddress.ip_address(ip.split("%")[0])
    return not (a.is_private or a.is_loopback or a.is_link_local or a.is_reserved
                or a.is_multicast or a.is_unspecified)


class PageFetcher:
    def __init__(self, client: httpx.AsyncClient | None = None,
                 resolver: Callable[[str], Awaitable[list[str]]] = default_resolver,
                 respect_robots: bool = True):
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(20.0, connect=10.0), headers={"User-Agent": USER_AGENT})
        self._resolver, self._robots_on = resolver, respect_robots
        self._robots: dict[str, RobotFileParser | None] = {}

    async def _check_host(self, url: str) -> None:
        p = urlparse(url)
        if p.scheme not in ("http", "https") or not p.hostname:
            raise FetchError("unsupported URL scheme")
        try:
            ips = [p.hostname] if _is_ip(p.hostname) else await self._resolver(p.hostname)
        except OSError:
            raise FetchError("host could not be resolved") from None
        if not ips or not all(_public(ip) for ip in ips):
            raise FetchError("refusing non-public address")

    async def _allowed(self, url: str) -> bool:
        if not self._robots_on:
            return True
        p = urlparse(url)
        origin = f"{p.scheme}://{p.netloc}"
        if origin not in self._robots:
            rp: RobotFileParser | None = RobotFileParser()
            try:
                r = await self._client.get(f"{origin}/robots.txt", headers={"User-Agent": USER_AGENT})
                if r.status_code >= 500:
                    rp = None  # cannot tell -> disallow
                elif r.status_code >= 400:
                    rp.parse([])  # no robots.txt -> allowed
                else:
                    rp.parse(r.text.splitlines())
            except httpx.HTTPError:
                rp = None
            self._robots[origin] = rp
        rp = self._robots[origin]
        return rp is not None and rp.can_fetch(USER_AGENT, url)

    async def fetch_text(self, url: str) -> FetchedPage:
        for _ in range(MAX_REDIRECTS + 1):
            await self._check_host(url)
            if not await self._allowed(url):
                raise FetchError("blocked by robots.txt")
            try:
                async with self._client.stream("GET", url, headers={"User-Agent": USER_AGENT},
                                               follow_redirects=False) as r:
                    if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
                        url = urljoin(url, r.headers["location"])
                        continue
                    if r.status_code != 200:
                        raise FetchError(f"HTTP {r.status_code}")
                    ctype = r.headers.get("content-type", "").lower()
                    if not (ctype.startswith("text/html") or ctype.startswith("text/plain")
                            or "xhtml" in ctype):
                        raise FetchError(f"unsupported content type ({ctype.split(';')[0] or 'unknown'})")
                    body = bytearray()
                    async for chunk in r.aiter_bytes():
                        body += chunk
                        if len(body) > MAX_BYTES:
                            break
                    html = bytes(body[:MAX_BYTES]).decode(r.encoding or "utf-8", errors="replace")
            except httpx.HTTPError as e:
                raise FetchError(f"network error ({type(e).__name__})") from None
            text = html_to_text(html) if "html" in ctype else html
            if not text.strip():
                raise FetchError("page has no readable text (may require JavaScript)")
            return FetchedPage(url, text)
        raise FetchError("too many redirects")


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False
