"""Static contracts for discoverability and open-source community surfaces."""

from __future__ import annotations

from pathlib import Path

from crewscore.scorers.structural_analysis import CONCEPTS


ROOT = Path(__file__).resolve().parents[1]


def test_static_discovery_has_robots_sitemap_and_structured_data():
    robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
    sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "Sitemap: https://crewscore.ai/sitemap.xml" in robots
    for route in ("https://crewscore.ai/", "https://crewscore.ai/security.html", "https://crewscore.ai/rules/", "https://crewscore.ai/docs/"):
        assert route in sitemap
    assert '"@type":"SoftwareApplication"' in index
    assert '"@type":"FAQPage"' in index
    assert 'href="rules/"' in index
    assert 'href="docs/"' in index
    assert 'href="security.html"' in index


def test_static_rules_page_is_the_complete_public_control_catalog():
    rules_page = (ROOT / "rules" / "index.html").read_text(encoding="utf-8")
    expected = {control.key for concepts in CONCEPTS.values() for control in concepts}
    missing = [control for control in expected if control not in rules_page]
    assert not missing, "static rules page dropped published controls: " + repr(missing)
    assert f"{len(expected)} public written guardrail controls" in rules_page


def test_community_governance_and_safe_reporting_surfaces_exist():
    for name in ("SECURITY.md", "CODE_OF_CONDUCT.md", ".github/pull_request_template.md"):
        assert (ROOT / name).exists(), name
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8").lower()
    conduct = (ROOT / "CODE_OF_CONDUCT.md").read_text(encoding="utf-8").lower()
    assert "privately" in security and "public issue" in security
    assert "github.com/shmindmaster/crewscore/security/advisories/new" in security
    assert "contributor covenant" in conduct
    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8").lower()
    assert "github.com/shmindmaster/crewscore/discussions" in contributing
    for name in ("false_positive.yml", "false_negative.yml", "framework_adapter.yml"):
        assert (ROOT / ".github" / "ISSUE_TEMPLATE" / name).exists(), name
    assert (ROOT / "docs" / "scoring-and-controls.md").exists()
    assert (ROOT / "docs" / "scoring-governance.md").exists()  # stable redirect
    assert (ROOT / "docs" / "github-action.md").exists()
    assert (ROOT / "docs" / "development.md").exists()
    assert (ROOT / "docs" / "architecture.md").exists()
    assert (ROOT / "docs" / "roadmap.md").exists()


def test_public_security_page_routes_to_the_private_reporting_channel_without_overclaiming():
    page = (ROOT / "security.html").read_text(encoding="utf-8").lower()
    assert "github.com/shmindmaster/crewscore/security/advisories/new" in page
    assert "dependabot security updates" in page
    assert "not a security certification" in page
