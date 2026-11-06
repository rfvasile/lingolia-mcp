"""A Lingolia rule page -> its title, its sections (one per linkable heading), the links in its text and its free exercise."""

from dataclasses import dataclass, field
from html.parser import HTMLParser

HEADINGS = {"h2": 0, "h3": 1, "h4": 2}  # tag -> depth in the heading path
SKIPPED = {"script", "style", "audio", "button", "figure", "form", "noscript", "svg", "template"}
BREAKS = {"p", "br", "div", "ul", "ol", "dl", "dt", "tr", "blockquote", "section", "h2", "h3", "h4", "h5"}
ITEMS = {"li", "dd"}
CELLS = {"td", "th"}


@dataclass
class Section:
    anchor: str
    heading: str  # its path, e.g. "Quand employer les pronoms ? › Les pronoms toniques"
    text: str


@dataclass
class Page:
    title: str
    sections: list[Section] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    exercise: str | None = None


def parse_page(html: str) -> Page:
    parser = _PageParser()
    parser.feed(html)
    parser.close()
    parser.flush()
    return parser.page


class _PageParser(HTMLParser):
    """Reads from the <h1> to the exercises, skipping the table of contents and what the site marks `indexer::stop`."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.page = Page(title="")
        self._reading = False  # after the h1
        self._done = False  # at the exercises
        self._exercises = False  # inside them, until </main>
        self._indexed = True
        self._skip: list = []  # [tag, depth] of the skipped element we are in
        self._heading: list | None = None  # [tag, anchor, parts] inside a heading
        self._tables = 0
        self._path: list[str] = []
        self._anchor, self._title, self._parts = "", "", []

    # Structure
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if self._exercises and tag == "a" and "exerci" in (href := attrs.get("href") or ""):
            self.page.exercise = self.page.exercise or href  # the free one comes first
        if self._done:
            return
        if self._skip:
            self._skip[1] += tag == self._skip[0]
        elif tag == "nav" and attrs.get("id") == "exercise-list" or attrs.get("id") == "exercises":
            self.flush()
            self._done = self._exercises = True
        elif tag == "h1":
            self._heading = [tag, "", []]
        elif not self._reading:
            return
        elif tag in SKIPPED or attrs.get("id") == "page-toc":
            self._skip = [tag, 1]
        elif tag in HEADINGS and attrs.get("id"):
            self._heading = [tag, attrs["id"], []]
        elif tag == "a" and self._indexed and (href := attrs.get("href") or "").startswith("/"):
            self.page.links.append(href.split("#")[0])
        elif tag == "table":
            self._tables += 1
            self._parts.append("\n")
        elif tag in BREAKS:
            self._parts.append(" " if self._tables and tag != "tr" else "\n")  # a table row stays on one line
        elif tag in ITEMS:
            self._parts.append("\n- ")

    def handle_endtag(self, tag):
        if tag == "main":
            self.flush()
            self._done, self._exercises = True, False
        if self._done:
            return
        if self._skip:
            self._skip[1] -= tag == self._skip[0]
            if self._skip[1] == 0:
                self._skip = []
        elif (heading := self._heading) and tag == heading[0]:
            self._end_heading(heading)
        elif tag in CELLS:
            self._parts.append(" | ")
        elif tag == "table":
            self._tables = max(0, self._tables - 1)
            self._parts.append("\n")

    def handle_data(self, data):
        if self._done or self._skip or not self._indexed:
            return
        if self._heading:
            self._heading[2].append(data)
        elif self._reading:
            self._parts.append(" ".join(data.splitlines()))  # source newlines are spaces; tags make lines

    def handle_comment(self, data):
        if "indexer::stop" in data:
            self._indexed = False
        elif "indexer::continue" in data:
            self._indexed = True

    # Sections
    def _end_heading(self, heading: list):
        tag, anchor, parts = heading
        text = " ".join("".join(parts).split())
        self._heading = None
        if tag == "h1":
            self.page.title = self._title = text.split(" – ")[0]
            self._reading = True
            return
        self.flush()
        self._path = self._path[: HEADINGS[tag]] + [text]
        self._anchor, self._title = anchor, " › ".join(self._path)

    def flush(self):
        """Close the section being read; one without text is dropped."""
        lines = (" ".join(line.split()).strip(" |") for line in "".join(self._parts).split("\n"))
        text = "\n".join(line for line in lines if line and line != "-")
        if text and self._title:
            self.page.sections.append(Section(self._anchor, self._title, text))
        self._parts = []
