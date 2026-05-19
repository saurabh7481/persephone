from __future__ import annotations

from typer.testing import CliRunner

from persephone.cli import main as cli_main


class FakeRegistry:
    load_errors: dict[str, str] = {}

    def discover(self) -> None:
        return None

    def list_all(self) -> list[dict[str, str]]:
        return [{"name": "sir_epidemic", "version": "0.1.0", "paradigm": "graph"}]


def test_plugins_list_command_shows_discovered_plugins(monkeypatch) -> None:
    monkeypatch.setattr(cli_main, "PluginRegistry", lambda: FakeRegistry())

    result = CliRunner().invoke(cli_main.app, ["plugins", "list"])

    assert result.exit_code == 0
    assert "sir_epidemic" in result.output
    assert "0.1.0" in result.output
    assert "graph" in result.output
