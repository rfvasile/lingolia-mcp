# lingolia-mcp

An MCP server for the French grammar and usage rules on [Lingolia](https://francais.lingolia.com/fr/).

| Tool | Returns |
|---|---|
| `find_rule()` | Every topic title, about 130. Call it once, then query with a title's words |
| `find_rule("pronoms adverbiaux y")` | The best sections, each with an excerpt, a link to that exact section and the topic's free exercise |

One tool, not two: an MCP client reads every tool's description on each turn.

It was built for the end-of-session bilan in [quest-voice-bridge](../quest-voice-bridge), but any MCP client can use it.

## Use

Needs Python ≥ 3.12 and [uv](https://docs.astral.sh/uv/).

```sh
uv run lingolia-mcp update                        # build the index: ~160 requests, one a second
uv run lingolia-mcp search "accord du participe passé avec avoir"
uv run lingolia-mcp serve                         # the MCP server, on stdio
```

The index lives in `~/.local/share/lingolia-mcp/rules.db`. `--data-dir` moves it. Run `update` again now and then; `status` shows when it was built.

As a stdio server in an MCP client config:

```json
{"command": "uv", "args": ["run", "--project", "/path/to/lingolia-mcp", "lingolia-mcp", "serve"]}
```

## What it reads

| Read | Left out |
|---|---|
| Rule pages under grammar, commonly confused words, sounds, numbers and dates, countries, writing (punctuation, registers) | Reading and listening texts, themed vocabulary, idioms, the conjugator, Lingolia Plus exercises |

- **Where the pages come from:** the French sitemap (`/fr/sitemap`), plus rule pages that their text links to.
- **How they are split:** one section per heading the site gives an anchor. Ads and the table of contents are dropped, as is everything the site marks `indexer::stop`.
- **Politeness:** it honours `robots.txt` and fetches one page a second. Search runs on the local index, never on Lingolia's search page, which `robots.txt` disallows.

The content belongs to Lingolia. The index stays local and is never committed, and answers carry short excerpts with a link.

## Code

| File | Role |
|---|---|
| `crawl.py` | Sitemap → rule pages, fetched politely |
| `page.py` | One page → title, sections, links, free exercise |
| `index.py` | SQLite full-text search, accents ignored, light stemming |
| `server.py` | `find_rule` |
| `cli.py` | `serve`, `update`, `status`, `search` |

`uv run pytest` runs the tests, on synthetic pages.
