import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_PREFIXES = (
    "weight-distribution-hitch/",
    "tests/fixtures/weight-distribution-hitch/",
)
PRIVATE_FILENAMES = (
    "customer-feedback-11-missed-patents-analysis.xlsx",
    "customer-feedback-missed-patents-highlighted.xlsx",
    "target-brands-and-amazon-product-url.png",
    "target-brands-and-amazon-product-url.txt",
    "vevor-weight-distribution-hitch-product-overview.jpg",
)


def tracked_paths() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [path.decode("utf-8") for path in result.stdout.split(b"\0") if path]


def test_public_repository_does_not_track_private_case_materials():
    paths = tracked_paths()

    assert not any(path.startswith(PRIVATE_PREFIXES) for path in paths)
    assert not any(Path(path).name in PRIVATE_FILENAMES for path in paths)
