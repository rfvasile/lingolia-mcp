from conftest import PRONOUNS, fetch

from lingolia_mcp.crawl import SITE, crawl
from lingolia_mcp.page import parse_page


def test_a_page_keeps_only_rule_text_under_linkable_headings():
    page = parse_page(PRONOUNS)

    assert page.title == "Les pronoms personnels"
    assert [(s.anchor, s.heading, s.text) for s in page.sections] == [
        ("a-quest-ce", "Qu’est-ce qu’un pronom personnel ?", "Les pronoms remplacent un nom."),
        ("a-toniques", "Quand employer les pronoms ? › Les pronoms toniques", "\n".join([
            "On emploie le pronom tonique après une préposition.",
            "Exemple :",
            "- Je pense à toi.",
            "sujet | tonique",
            "je | moi",
            "Voir aussi les pronoms réfléchis.",
        ])),
    ], "no ads, contents, script or exercises; a heading without text is dropped"
    assert page.links == ["/fr/grammaire/les-pronoms/pronoms-reflechis"]
    assert page.exercise == "https://francais.lingolia.com/fr/grammaire/les-pronoms/pronoms-personnels/exercices"


def test_crawl_reads_rule_pages_with_their_exercise_and_follows_rule_links():
    pages, failed = crawl(fetch, log=lambda _: None, pause=0)

    assert {p.path: p.exercise for p in pages} == {
        "/fr/grammaire/les-pronoms/pronoms-personnels": f"{SITE}/fr/grammaire/les-pronoms/pronoms-personnels/exercices",
        "/fr/grammaire/les-pronoms/pronoms-reflechis": None,
    }, "the conjugator, reading texts and pages robots.txt disallows are left out; a footer link is no exercise"
    assert failed == 1, "the verbs page timed out; a 404 from a stale exercise link is no failure"
