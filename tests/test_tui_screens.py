"""Unit tests for the pure helpers behind the Textual screens.

The widgets themselves are covered by ``App.run_test()`` coverage; these tests
pin the logic that is easier to break than to click through: the numeric input
rules and the planner preview rendering.
"""

from __future__ import annotations

import pytest

textual = pytest.importorskip("textual")


def test_planner_editor_error_messages_are_distinct():
    pytest.importorskip("textual")
    from asteroidpy.interface._tui_screens import (
        PLANNER_ERROR_MESSAGES,
        _planner_error_message,
    )

    messages = {
        reason: _planner_error_message(reason) for reason in PLANNER_ERROR_MESSAGES
    }
    assert set(messages) == {
        "not_a_number",
        "not_an_integer",
        "out_of_range",
        "zero_sum",
    }
    assert all(text for text in messages.values())
    assert len(set(messages.values())) == len(messages)
    # An unknown reason must still produce a message, not a crash or an empty string.
    assert _planner_error_message("brand_new_reason")


def test_planner_weight_labels_follow_the_known_factors():
    pytest.importorskip("textual")
    from asteroidpy.interface._tui_screens import _planner_weight_labels

    labels = _planner_weight_labels(
        {"cloud": 0.4, "seeing": 0.25, "transparency": 0.15, "moon": 0.2}
    )
    assert labels == [
        "Cloud cover: 0.400",
        "Seeing: 0.250",
        "Transparency: 0.150",
        "Moon: 0.200",
    ]


def test_planner_preview_lines_lists_weights_and_ranked_nights():
    pytest.importorskip("textual")
    astropy_time = pytest.importorskip("astropy.time")
    from asteroidpy.interface._tui_screens import _planner_preview_lines

    weights = {"cloud": 0.4, "seeing": 0.25, "transparency": 0.15, "moon": 0.2}
    lines = _planner_preview_lines([], weights)
    assert "Weights used for the score:" in lines
    assert "Cloud cover: 0.400" in lines
    assert "No weather forecast available." in lines

    night = {
        "date": "2026-09-26",
        "start": astropy_time.Time("2026-09-26 17:30:00"),
        "end": astropy_time.Time("2026-09-27 04:30:00"),
        "score": 87.5,
    }
    lines = _planner_preview_lines([night], weights)
    assert "Best nights with these weights:" in lines
    assert lines[-1] == "1. 2026-09-26  17:30 - 04:30 UTC  score 87.5"


def test_clamped_int_reports_typos_and_out_of_range_values():
    from asteroidpy.interface._tui_screens import _clamped_int

    assert _clamped_int("12", 1, 30) == (12, False)
    assert _clamped_int(" 30 ", 1, 30) == (30, False)
    # Out of range: clamped, and the caller must tell the user.
    assert _clamped_int("0", 1, 30) == (1, True)
    assert _clamped_int("999", 1, 30) == (30, True)
    # Not a whole number: refused, so a typo is not silently replaced.
    assert _clamped_int("", 1, 30) is None
    assert _clamped_int("abc", 1, 30) is None
    assert _clamped_int("3.5", 1, 30) is None


def test_validate_horizon_degrees_accepts_only_altitudes():
    from asteroidpy.interface._tui_screens import _validate_horizon_degrees

    assert _validate_horizon_degrees("0") == 0.0
    assert _validate_horizon_degrees(" 20.5 ") == 20.5
    assert _validate_horizon_degrees("90") == 90.0
    assert _validate_horizon_degrees("-1") is None
    assert _validate_horizon_degrees("90.1") is None
    assert _validate_horizon_degrees("nan") is None
    assert _validate_horizon_degrees("inf") is None
    assert _validate_horizon_degrees("") is None
    assert _validate_horizon_degrees("ten") is None


def test_best_night_night_count_cap_is_documented():
    # The screen clamps the requested nights to this range and documents it.
    from asteroidpy.interface._tui_screens import _MAX_BEST_NIGHT_NIGHTS

    assert 1 <= _MAX_BEST_NIGHT_NIGHTS <= 30


def test_whatsup_error_labels_cover_every_scraping_reason():
    from asteroidpy.errors import (
        REASON_HTTP_STATUS,
        REASON_NETWORK_ERROR,
        REASON_TOKEN_NOT_FOUND,
    )
    from asteroidpy.interface._tui_screens import WHATSUP_ERROR_LABELS

    # Every reason scheduling can raise must have a translated label, or the
    # notification would fall back to a raw internal identifier.
    assert set(WHATSUP_ERROR_LABELS) == {
        REASON_HTTP_STATUS,
        REASON_NETWORK_ERROR,
        REASON_TOKEN_NOT_FOUND,
    }
    assert all(WHATSUP_ERROR_LABELS.values())
