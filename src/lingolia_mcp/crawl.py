"""Lingolia's French rule pages, read politely: robots.txt honoured, one page a second."""

import re
import time
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

from lingolia_mcp.page import Section, parse_page

SITE = "https://francais.lingolia.com"
SITEMAP = "/fr/sitemap"
USER_AGENT = "lingolia-mcp (personal use)"
AREAS = (  # rules, not reading texts or themed vocabulary
    "/fr/grammaire/",
    "/fr/vocabulaire/mots-a-ne-pas-confondre/",
    "/fr/vocabulaire/mots-confondus",
    "/fr/vocabulaire/les-sons",
    "/fr/vocabulaire/nombres-date-et-heure",
    "/fr/vocabulaire/pays-et-gentiles",
    "/fr/atelier-decriture/",
)
NOT_RULES = ("/fr/grammaire/conjugueur",)
MAX_PAGES = 400
HREF = re.compile(r'href="(/fr/[^"#?]*)"')

Fetch = Callable[[str], str]


@dataclass
class RulePage:
    path: str
    title: str
    exercise: str | None  # URL of the topic's free exercise
    sections: list[Section]


def fetch_html(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def rule_paths(paths: Iterable[str]) -> list[str]:
    """The rule pages among `paths`; an exercise stands for the page above it."""
    rules: list[str] = []
    for path in (p.rstrip("/") for p in paths):
        if not path.startswith(AREAS) or path.startswith(NOT_RULES):
            continue
        parent, last = path.rsplit("/", 1)
        if (rule := parent if "exerci" in last else path) not in rules:
            rules.append(rule)
    return rules


def crawl(fetch: Fetch = fetch_html, log=print, pause: float = 1.0) -> tuple[list[RulePage], int]:
    """Every rule page in the sitemap, plus rule pages their text links to; also how many failed."""
    robots = RobotFileParser()
    robots.parse(fetch(f"{SITE}/robots.txt").splitlines())
    todo = rule_paths(HREF.findall(fetch(SITE + SITEMAP)))
    known, pages, failed = set(todo), [], 0

    while todo and len(pages) + failed < MAX_PAGES:
        path = todo.pop(0)
        if not robots.can_fetch(USER_AGENT, SITE + path):
            continue
        time.sleep(pause)
        try:
            page = parse_page(fetch(SITE + path))
        except OSError as error:
            if getattr(error, "code", None) == 404:
                continue  # guessed from an exercise link that outlived its page
            log(f"✗ {path}: {error}")
            failed += 1
            continue

        # Overview pages are only links: followed, not kept
        if page.sections:
            exercise = urljoin(SITE, page.exercise) if page.exercise else None
            pages.append(RulePage(path, page.title, exercise, page.sections))
            log(f"✓ {page.title}: {len(page.sections)} sections")
        for link in rule_paths(page.links):
            if link not in known:
                known.add(link)
                todo.append(link)
    return pages, failed
