"""Public attribution must distinguish the maintainer from the company context."""

from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def test_readme_names_creator_and_operating_context_without_bio_claims():
    text = (REPO / "README.md").read_text(encoding="utf-8")
    assert "Created and maintained by **Sarosh Hussain**" in text
    assert "**Pendoah** is the company" in text
    assert "operating context for this project" in text
    assert "code, tests, and cited validation material" in text


def test_site_metadata_and_footer_name_creator_and_company_context():
    text = (REPO / "index.html").read_text(encoding="utf-8")
    assert '<meta name="author" content="Sarosh Hussain">' in text
    assert '"creator":{"@type":"Person","name":"Sarosh Hussain"}' in text
    assert '"maintainer":{"@type":"Person","name":"Sarosh Hussain"}' in text
    assert '"publisher":{"@type":"Organization","name":"Pendoah"}' in text
    assert "Created and maintained by <strong>Sarosh Hussain</strong>" in text
    assert "Pendoah is the company operating context" in text


def test_package_and_action_metadata_name_sarosh_as_author_and_maintainer():
    pyproject = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    package = (REPO / "package.json").read_text(encoding="utf-8")
    action = (REPO / "action.yml").read_text(encoding="utf-8")
    assert 'name = "Sarosh Hussain"' in pyproject
    assert "maintainers = [" in pyproject
    assert '"author": "Sarosh Hussain"' in package
    assert "author: Sarosh Hussain" in action


def test_launch_material_names_creator_without_claiming_company_as_evidence():
    paths = (
        REPO / "_production" / "launch" / "launch-copy.md",
        REPO / "_production" / "launch" / "linkedin-and-showhn.md",
        REPO / "_production" / "launch" / "answer-bank.md",
    )
    for path in paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        assert "Sarosh Hussain" in text
        assert "Pendoah" in text
        assert "repository" in text
