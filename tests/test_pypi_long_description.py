"""PyPI must receive a self-contained, portable long description."""

from __future__ import annotations

import io
import tarfile
import tomllib
import zipfile
from pathlib import Path

from scripts.check_dist_metadata import (
    _console_safe,
    check_artifacts,
    find_nonportable_targets,
)

ROOT = Path(__file__).resolve().parents[1]


def _metadata(description: str) -> bytes:
    return (
        "Metadata-Version: 2.4\n"
        "Name: crewscore\n"
        "Version: 0.0.0\n"
        "Description-Content-Type: text/markdown\n"
        "\n"
        f"{description}\n"
    ).encode("utf-8")


def _dist_pair(directory: Path, description: str) -> tuple[Path, Path]:
    wheel = directory / "crewscore-0.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, mode="w") as archive:
        archive.writestr("crewscore-0.0.0.dist-info/METADATA", _metadata(description))

    sdist = directory / "crewscore-0.0.0.tar.gz"
    payload = _metadata(description)
    info = tarfile.TarInfo("crewscore-0.0.0/PKG-INFO")
    info.size = len(payload)
    with tarfile.open(sdist, mode="w:gz") as archive:
        archive.addfile(info, io.BytesIO(payload))
    return wheel, sdist


def test_link_detector_covers_markdown_html_and_reference_targets():
    description = """
[doc](docs/guide.md)
![plot](images/plot.svg)
[reference]: ./CHANGELOG.md
<a href="ROADMAP.md">Roadmap</a>
<img src='../hero.png'>
<a href=docs/unquoted.md>Unquoted</a>
"""
    assert find_nonportable_targets(description) == [
        ("markdown link", "docs/guide.md"),
        ("markdown image", "images/plot.svg"),
        ("markdown reference", "./CHANGELOG.md"),
        ("html href", "ROADMAP.md"),
        ("html src", "../hero.png"),
        ("html href", "docs/unquoted.md"),
    ]


def test_console_diagnostics_escape_non_ascii_content():
    rendered = _console_safe("arrow \u2192 caf\u00e9")
    rendered.encode("ascii")
    assert "\\u2192" in rendered
    assert "\\xe9" in rendered


def test_link_detector_allows_absolute_urls_fragments_and_fenced_examples():
    description = """
[site](https://crewscore.ai)
[email](mailto:sarosh@pendoah.ai)
[section](#usage)
<img src="https://raw.githubusercontent.com/shmindmaster/crewscore/main/docs/demo.svg">

```markdown
[repository-relative example](docs/example.md)
```
"""
    assert find_nonportable_targets(description) == []


def test_link_detector_rejects_malformed_http_urls_without_a_host():
    assert find_nonportable_targets("[broken](https:/github.com/file)") == [
        ("markdown link", "https:/github.com/file")
    ]


def test_built_wheel_and_sdist_metadata_are_both_inspected(tmp_path: Path):
    _dist_pair(tmp_path, "[broken](docs/validation.md)")
    violations = check_artifacts([tmp_path])
    assert len(violations) == 2
    assert any(".whl:" in violation for violation in violations)
    assert any(".tar.gz:" in violation for violation in violations)


def test_repository_readme_is_the_portable_package_description():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["readme"] == "README.md"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert find_nonportable_targets(readme) == []
