"""Extraction has to survive MkDocs Material's several ways of writing a fence."""

from assay.blocks import extract, runnable, strip_prompts


def test_plain_fence():
    blocks = extract("```sql\nSELECT 1;\n```\n", "p.md")
    assert len(blocks) == 1
    assert blocks[0].lang == "sql"
    assert blocks[0].kind == "sql"
    assert blocks[0].body == "SELECT 1;"


def test_material_brace_info_string():
    text = '```{.bash data-prompt="$"}\nsudo apt-get update\n```\n'
    (block,) = extract(text, "p.md")
    assert block.lang == "bash"
    assert block.kind == "shell"


def test_spaced_brace_info_string():
    text = "``` { .bash .no-copy }\nls\n```\n"
    (block,) = extract(text, "p.md")
    assert block.lang == "bash"


def test_indented_fence_inside_list_item_is_dedented():
    text = "1. Do this:\n\n    ```sql\n    SELECT 1;\n    ```\n"
    (block,) = extract(text, "p.md")
    assert block.body == "SELECT 1;", "leading indent must not reach the database"


def test_line_number_points_at_the_opening_fence():
    text = "# Title\n\nsome prose\n\n```sql\nSELECT 1;\n```\n"
    (block,) = extract(text, "p.md")
    assert block.line == 5
    assert block.location() == "p.md:5"


def test_sample_output_in_an_example_admonition_is_not_runnable():
    text = (
        '??? example "Sample output"\n'
        "    ```sql\n"
        "    postgres=# SELECT 1;\n"
        "    ---------------------\n"
        "    (1 row)\n"
        "    ```\n"
    )
    blocks = extract(text, "p.md")
    assert len(blocks) == 1
    assert list(runnable(blocks)) == [], "sample output is for comparing, not running"


def test_prompts_are_stripped():
    assert strip_prompts("$ ls -la") == "ls -la"
    assert strip_prompts("postgres=# SELECT 1;") == "SELECT 1;"


def test_non_executable_languages_are_ignored():
    text = "```ini\narchive-async=n\n```\n"
    assert list(runnable(extract(text, "p.md"))) == []
