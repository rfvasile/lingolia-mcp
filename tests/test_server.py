from fastmcp import Client

from lingolia_mcp.crawl import SITE
from lingolia_mcp.index import Index
from lingolia_mcp.server import NO_INDEX, NO_MATCH, build_server


async def call(index, tool, **args):
    async with Client(build_server(index)) as client:
        return (await client.call_tool(tool, args)).data


async def test_find_rule_links_the_best_section_and_its_exercise(index):
    found = await call(index, "find_rule", query="pronoms toniques apres une preposition")

    best = found["rules"][0]
    assert best["url"] == f"{SITE}/fr/grammaire/les-pronoms/pronoms-personnels#a-toniques", "plural, unaccented query"
    assert best["exercise"] == f"{SITE}/fr/grammaire/les-pronoms/pronoms-personnels/exercices"
    assert best["excerpt"].startswith("On emploie le pronom tonique")


async def test_no_query_names_every_indexed_page(index):
    assert (await call(index, "find_rule"))["topics"] == ["Les pronoms personnels", "Les pronoms réfléchis"]


async def test_tools_say_what_to_do_when_they_have_nothing(index, tmp_path):
    missing = Index(tmp_path / "none.db")
    assert (await call(index, "find_rule", query="subjonctif"))["hint"] == NO_MATCH
    assert (await call(missing, "find_rule", query="pronoms"))["hint"] == NO_INDEX
    assert (await call(missing, "find_rule"))["hint"] == NO_INDEX
