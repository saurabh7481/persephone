from __future__ import annotations

from pathlib import Path

FORBIDDEN_TERMS = (
    "infected_count",
    "susceptible_count",
    "recovered_count",
    "p_infect",
    "p_recover",
    "initially_infected",
    "temperature_min",
    "temperature_max",
    "center_temperature",
)

SCAN_ROOTS = [
    Path("src/persephone"),
    Path("sdk/src"),
    Path("ui/src/lib"),
]

ALLOWED_FILES = {
    Path("src/persephone/api/routes/examples.py"),
}


def test_shared_platform_code_does_not_hardcode_example_domain_terms() -> None:
    leaks: list[str] = []
    for root in SCAN_ROOTS:
        for path in root.rglob("*"):
            if (
                path in ALLOWED_FILES
                or not path.is_file()
                or path.suffix not in {".py", ".ts"}
                or path.name.endswith(".test.ts")
            ):
                continue
            text = path.read_text(encoding="utf-8")
            for term in FORBIDDEN_TERMS:
                if term in text:
                    leaks.append(f"{path}:{term}")

    assert leaks == []
