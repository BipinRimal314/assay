"""Regression tests pinned to the real defects in the vendored pg_tde corpus.

Each test names a defect that was first found by executing the page against a
live Percona Server for PostgreSQL 18.6.1, then encoded as a rule. If a rule
stops firing on the corpus, either upstream fixed the docs (good, update the
corpus and delete the test) or the rule broke (bad, and this catches it).

Corpus: percona/pg_tde documentation, vendored under corpus/. See
findings/pg_tde-2.2.2.md for the write-up of each one.
"""

import os

import pytest

from assay.lint import lint_page

DOCS = os.path.join(os.path.dirname(__file__), "..", "corpus", "pg_tde",
                    "documentation", "docs")


def findings_for(relpath, expect_major="18"):
    path = os.path.join(DOCS, relpath)
    if not os.path.exists(path):
        pytest.skip("corpus not vendored: " + relpath)
    with open(path, encoding="utf-8") as fh:
        return lint_page(fh.read(), relpath, expect_major=expect_major)


def rules(findings, severity=None):
    return {f.rule for f in findings if severity is None or f.severity == severity}


def test_install_page_ships_an_unrendered_placeholder_in_a_shell_block():
    """`sudo apt-get install -y percona-pg-tde(pg-version)`

    Parentheses are shell metacharacters, so this is not a wrong package name,
    it is a syntax error. Confirmed by execution: bash exits 2 with
    "syntax error near unexpected token `('".
    """
    found = findings_for("apt.md")
    assert "L001" in rules(found, "fail")


def test_the_same_placeholder_bug_is_systematic_not_isolated():
    """It appears on the apt, yum and uninstall pages, so it is a template
    defect rather than one page's typo."""
    pages = ["apt.md", "yum.md", "how-to/uninstall.md"]
    hit = [p for p in pages if "L001" in rules(findings_for(p), "fail")]
    assert len(hit) == len(pages), "expected the placeholder on every install page"


def test_setup_page_tags_a_shell_command_as_sql():
    """`psql -d template1 -c 'CREATE EXTENSION pg_tde;'` inside a ```sql fence.

    A reader trusts the tag. Pasted into psql it raises
    ERROR: syntax error at or near "psql".
    """
    found = findings_for("setup.md")
    assert "L002" in rules(found, "fail")


def test_validation_page_checks_a_table_it_never_created():
    """The page creates `albums`, then calls pg_tde_is_encrypted('table_name')."""
    found = findings_for("test.md")
    drift = [f for f in found if f.rule == "L003" and f.severity == "fail"]
    assert drift, "expected identifier drift on test.md"
    assert "albums" in drift[0].summary


def test_keyring_page_inspects_test1_after_creating_customer_table():
    found = findings_for("global-key-provider-configuration/keyring.md")
    drift = [f for f in found if f.rule == "L003" and f.severity == "fail"]
    assert drift
    assert "test1" in drift[0].summary and "customer_table" in drift[0].summary


def test_setup_page_still_hardcodes_the_previous_major_version():
    """`sudo systemctl restart postgresql-17` in a doc set that ships 18."""
    found = findings_for("setup.md")
    assert "L004" in rules(found, "warn")


# --- calibration ---------------------------------------------------------
# These pin the rule's boundaries. Uncalibrated, L003 reported eleven failures
# on this corpus, of which four were real. The rest were system catalogs and
# pages that deliberately use a generic table name.

def test_system_catalogs_are_not_identifier_drift():
    """Nobody creates pg_stat_replication. Querying it is not a defect."""
    found = findings_for("replication.md")
    fails = [f for f in found if f.rule == "L003" and f.severity == "fail"]
    assert not any("pg_stat_replication" in f.summary for f in fails)


def test_a_page_that_creates_nothing_is_a_fragment_not_a_defect():
    """decrypt.md uses `mytable` as a stand-in and creates no tables. The
    reader is meant to substitute their own, so this is a note, not a failure."""
    found = findings_for("how-to/decrypt.md")
    l003 = [f for f in found if f.rule == "L003"]
    assert l003, "expected the rule to see these references"
    assert all(f.severity == "note" for f in l003)
