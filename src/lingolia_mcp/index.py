"""The rule sections in SQLite full-text search, accents ignored."""

import os
import re
import sqlite3
import time
import unicodedata
from contextlib import closing
from pathlib import Path

from lingolia_mcp.crawl import SITE, RulePage

EXCERPT_CHARS = 700
WEIGHTS = (4.0, 2.0, 1.0)  # title, heading, text
STOPWORDS = set(
    "le la les l un une des de du d et ou a au aux en dans sur pour par avec sans "
    "ce cet cette ces se sa son ses que qu qui dont ne pas plus est sont il elle on y".split()
)
ENDINGS = ("es", "er", "ez", "s", "x", "e")  # so "accorder" finds "accord", "toniques" "tonique"


class Index:
    def __init__(self, path: Path):
        self.path = path

    def replace(self, pages: list[RulePage]) -> None:
        """Build beside the old index, then swap: a running server never reads a half-built one."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.unlink(missing_ok=True)
        rows = [(p.title, s.heading, s.text, p.path, s.anchor, p.exercise) for p in pages for s in p.sections]
        with closing(sqlite3.connect(tmp)) as db, db:
            db.execute(
                "create virtual table sections using fts5(title, heading, text, path unindexed, anchor unindexed,"
                " exercise unindexed, tokenize='unicode61 remove_diacritics 2')"
            )
            db.execute("create table meta (built_at real, pages integer)")
            db.executemany("insert into sections values (?, ?, ?, ?, ?, ?)", rows)
            db.execute("insert into meta values (?, ?)", (time.time(), len(pages)))
        os.replace(tmp, self.path)

    def search(self, query: str, limit: int = 3) -> list[dict] | None:
        """The best sections for `query`; None without an index."""
        if not self.path.exists():
            return None
        match = " OR ".join(f'"{term}"*' for term in terms(query))
        if not match:
            return []
        with closing(self._connect()) as db:
            rows = db.execute(
                "select title, heading, text, path, anchor, exercise from sections"
                " where sections match ? order by bm25(sections, ?, ?, ?) limit ?",
                (match, *WEIGHTS, limit),
            ).fetchall()
        return [rule(*row) for row in rows]

    def status(self) -> dict | None:
        if not self.path.exists():
            return None
        with closing(self._connect()) as db:
            built_at, pages = db.execute("select built_at, pages from meta").fetchone()
            (sections,) = db.execute("select count(*) from sections").fetchone()
        return {"pages": pages, "sections": sections, "built": time.strftime("%Y-%m-%d %H:%M", time.localtime(built_at))}

    def topics(self) -> list[str] | None:
        """Every page title, ordered by path so related topics sit together; None without an index."""
        if not self.path.exists():
            return None
        with closing(self._connect()) as db:
            return [title for (title,) in db.execute("select title from sections group by path order by path")]

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)


def terms(query: str) -> list[str]:
    """Query words, unaccented, without stopwords, cut to a stem."""
    plain = "".join(c for c in unicodedata.normalize("NFKD", query.casefold()) if not unicodedata.combining(c))
    return [stem(w) for w in re.findall(r"\w+", plain) if len(w) > 1 and w not in STOPWORDS]


def stem(word: str) -> str:
    for ending in ENDINGS:
        if word.endswith(ending) and len(word) - len(ending) >= 4:
            return word[: -len(ending)]
    return word


def rule(title: str, heading: str, text: str, path: str, anchor: str, exercise: str | None) -> dict:
    return {
        "topic": title,
        "section": heading,
        "url": f"{SITE}{path}#{anchor}" if anchor else SITE + path,
        "excerpt": excerpt(text),
        "exercise": exercise,
    }


def excerpt(text: str) -> str:
    """The section's start, cut at a line (or else a word) before EXCERPT_CHARS."""
    if len(text) <= EXCERPT_CHARS:
        return text
    cut = text.rfind("\n", 0, EXCERPT_CHARS)
    if cut < EXCERPT_CHARS // 2:
        cut = text.rfind(" ", 0, EXCERPT_CHARS)
    return text[:cut] + " …"
