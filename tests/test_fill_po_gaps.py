"""Tests for scripts/fill_po_gaps.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

polib = pytest.importorskip("polib")

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def fill_po_gaps():
    path = REPO_ROOT / "scripts" / "fill_po_gaps.py"
    spec = importlib.util.spec_from_file_location("fill_po_gaps", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fill_po_gaps_fills_missing_and_clears_fuzzy(
    monkeypatch, tmp_path, fill_po_gaps
):
    locales_dir = tmp_path / "locales"
    en_dir = locales_dir / "en" / "LC_MESSAGES"
    en_dir.mkdir(parents=True)

    po_path = en_dir / "base.po"
    po_path.write_text(
        "\n".join(
            [
                'msgid ""',
                'msgstr ""',
                r'"Content-Type: text/plain; charset=UTF-8\n"',
                "",
                "#, fuzzy",
                'msgid "GAPTEST_HELLO"',
                'msgstr ""',
                "",
                'msgid "GAPTEST_WORLD"',
                'msgstr ""',
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(fill_po_gaps, "LOCALES", locales_dir)
    monkeypatch.setattr(fill_po_gaps, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        fill_po_gaps,
        "GAP_STRINGS",
        {
            "GAPTEST_HELLO": {"en": "", "it": "Ciao"},
            "GAPTEST_WORLD": {"en": "", "it": "Mondo"},
        },
    )

    calls = []

    def fake_run(cmd, check=True, cwd=None):
        calls.append((tuple(cmd), check, cwd))

    monkeypatch.setattr(fill_po_gaps.subprocess, "run", fake_run)
    monkeypatch.setattr(fill_po_gaps.shutil, "which", lambda _cmd: "/fake/msgfmt")

    fill_po_gaps.main()

    po = polib.pofile(str(po_path))
    by_id = {e.msgid: e for e in po if e.msgid}
    assert by_id["GAPTEST_HELLO"].msgstr == "GAPTEST_HELLO"
    assert not by_id["GAPTEST_HELLO"].fuzzy
    assert by_id["GAPTEST_WORLD"].msgstr == "GAPTEST_WORLD"

    assert len(calls) == 1
    cmd, check, cwd = calls[0]
    assert cmd[0] == "/fake/msgfmt"
    assert check is True
    assert cwd == str(tmp_path)


def test_fill_po_gaps_skips_msgfmt_when_not_installed(
    monkeypatch, tmp_path, fill_po_gaps
):
    locales_dir = tmp_path / "locales"
    en_dir = locales_dir / "en" / "LC_MESSAGES"
    en_dir.mkdir(parents=True)
    po_path = en_dir / "base.po"
    po_path.write_text(
        "\n".join(
            [
                'msgid ""',
                'msgstr ""',
                r'"Content-Type: text/plain; charset=UTF-8\n"',
                "",
                'msgid "GAPTEST_ONLY"',
                'msgstr ""',
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(fill_po_gaps, "LOCALES", locales_dir)
    monkeypatch.setattr(fill_po_gaps, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        fill_po_gaps,
        "GAP_STRINGS",
        {"GAPTEST_ONLY": {"en": "", "it": "solo"}},
    )

    def boom(*_a, **_kw):
        raise AssertionError("subprocess.run should not run without msgfmt")

    monkeypatch.setattr(fill_po_gaps.subprocess, "run", boom)
    monkeypatch.setattr(fill_po_gaps.shutil, "which", lambda _cmd: None)

    fill_po_gaps.main()

    po = polib.pofile(str(po_path))
    entry = next(e for e in po if e.msgid == "GAPTEST_ONLY")
    assert entry.msgstr == "GAPTEST_ONLY"
