"""Public attribution names the independent maintainer and no company."""

from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
CONTACT_EMAIL = "sarosh.hussain@gmail.com"


def test_readme_names_independent_maintainer_without_bio_claims():
    text = (REPO / "README.md").read_text(encoding="utf-8")
    assert "Created and maintained by **Sarosh Hussain**, an independent open-source" in text
    assert "operating context" not in text
    assert "code, tests, and cited validation material" in text


def test_site_metadata_and_footer_name_independent_maintainer():
    text = (REPO / "index.html").read_text(encoding="utf-8")
    assert '<meta name="author" content="Sarosh Hussain">' in text
    assert '"creator":{"@type":"Person","name":"Sarosh Hussain"}' in text
    assert '"maintainer":{"@type":"Person","name":"Sarosh Hussain"}' in text
    assert '"publisher"' not in text
    assert '"@type":"Organization"' not in text
    assert "Created and maintained by <strong>Sarosh Hussain</strong>, an independent open-source maintainer" in text
    assert "operating context" not in text


def test_package_and_action_metadata_name_sarosh_as_author_and_maintainer():
    pyproject = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    package = (REPO / "package.json").read_text(encoding="utf-8")
    action = (REPO / "action.yml").read_text(encoding="utf-8")
    assert 'name = "Sarosh Hussain"' in pyproject
    assert "maintainers = [" in pyproject
    assert pyproject.count(f'email = "{CONTACT_EMAIL}"') == 2
    assert '"author": "Sarosh Hussain"' in package
    assert "author: Sarosh Hussain" in action


def test_license_and_contacts_name_the_individual_maintainer():
    license_text = (REPO / "LICENSE").read_text(encoding="utf-8").replace("\r\n", "\n")
    assert "Copyright (c) 2026 Sarosh Hussain\n" in license_text
    for name in ("CODE_OF_CONDUCT.md", "SECURITY.md", "security.html"):
        text = (REPO / name).read_text(encoding="utf-8")
        assert CONTACT_EMAIL in text, name
        assert "operating context" not in text, name


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
        assert "operating context" not in text
        assert "repository" in text
