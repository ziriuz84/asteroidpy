import asyncio
import importlib
import json
import pathlib
import time
from configparser import ConfigParser
from typing import Any

import httpx
import pytest
import requests


class FakeRequestsSuccessResponse:
    """Minimal response object for ``observing_target_list_scraper`` mocks."""

    def __init__(self, content: bytes, status_code: int = 200) -> None:
        self.content = content
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(response=None)


@pytest.fixture(scope="module")
def sch():
    # Ensure heavy optional deps exist; otherwise skip these tests entirely
    pytest.importorskip("astropy")
    pytest.importorskip("astroplan")
    pytest.importorskip("astroquery")
    pytest.importorskip("bs4")
    pytest.importorskip("httpx")
    pytest.importorskip("requests")

    import importlib

    return importlib.import_module("asteroidpy.scheduling")


@pytest.fixture(autouse=True)
def no_load_config(monkeypatch, sch):
    # Avoid filesystem reads from configuration
    monkeypatch.setattr(sch.configuration, "load_config", lambda conf: None)


@pytest.fixture()
def fresh_config() -> ConfigParser:
    c = ConfigParser()
    c["General"] = {"lang": "en"}
    c["Observatory"] = {
        "place": "",
        "latitude": "45.0",
        "longitude": "9.0",
        "altitude": "100.0",
        "obs_name": "Obs",
        "observer_name": "John",
        "mpc_code": "C10",
        # Virtual horizon thresholds (degrees)
        "nord_altitude": "10",
        "south_altitude": "10",
        "east_altitude": "10",
        "west_altitude": "10",
    }
    return c


def test_weather_time_basic(sch):
    assert sch.weather_time("2025010100", 5) == "01/01 05:00"
    assert sch.weather_time("2024013123", 2) == "01/02 01:00"


def test_skycoord_format_ra_dec(sch):
    assert sch.skycoord_format("12 30 00", "ra") == "12h30m00s"
    assert sch.skycoord_format("-30 15 30", "dec") == "-30d15m30s"


def test_skycoord_format_invalid_inputs_return_original(sch):
    # Wrong number of fields
    assert sch.skycoord_format("12 30", "ra") == "12 30"
    # Non-numeric fields
    assert sch.skycoord_format("12 aa 00", "ra") == "12 aa 00"
    assert sch.skycoord_format("+x 10 10", "dec") == "+x 10 10"
    # Accept colon-separated and zero-pad
    assert sch.skycoord_format("12:3:5", "ra") == "12h03m05s"
    # Unknown coordid falls back to original
    assert sch.skycoord_format("12 30 00", "foo") == "12 30 00"


def test_httpx_get_and_post(monkeypatch, sch):
    class DummyResponse:
        def __init__(self, payload: dict[str, Any]):
            self._payload = payload
            self.text = "<ok/>"
            self.status_code = 200
            self.headers = {}

        def json(self) -> dict[str, Any]:
            return self._payload

    class DummyAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, params=None):
            return DummyResponse({"url": url, "params": params})

        async def post(self, url, data=None, headers=None):
            return DummyResponse({"url": url, "data": data})

    monkeypatch.setattr(sch.httpx, "AsyncClient", lambda *a, **k: DummyAsyncClient())

    # Exercise get
    data, status = asyncio.run(sch.httpx_get("https://example.com", {"q": "1"}, "json"))
    assert status == 200 and data["params"] == {"q": "1"}
    text, status = asyncio.run(sch.httpx_get("https://example.com", {}, "text"))
    assert status == 200 and text == "<ok/>"

    # Exercise post
    data, status = asyncio.run(sch.httpx_post("https://example.com", {"a": 1}, "json"))
    assert status == 200 and data["data"] == {"a": 1}
    text, status = asyncio.run(sch.httpx_post("https://example.com", {}, "text"))
    assert status == 200 and text == "<ok/>"


def test_httpx_get_post_non_200(monkeypatch, sch):
    class DummyResponse:
        def __init__(self, payload: dict[str, Any], status_code: int, text: str):
            self._payload = payload
            self.text = text
            self.status_code = status_code
            self.headers = {}

        def json(self) -> dict[str, Any]:
            return self._payload

    class DummyAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, params=None):
            return DummyResponse({"error": "not found"}, 404, "Not Found")

        async def post(self, url, data=None, headers=None):
            return DummyResponse({"error": "bad request"}, 400, "Bad Request")

    monkeypatch.setattr(sch.httpx, "AsyncClient", lambda *a, **k: DummyAsyncClient())

    data, status = asyncio.run(sch.httpx_get("https://example.com/miss", {}, "json"))
    assert status == 404 and data == {"error": "not found"}

    text, status = asyncio.run(sch.httpx_get("https://example.com/miss", {}, "text"))
    assert status == 404 and text == "Not Found"

    data, status = asyncio.run(sch.httpx_post("https://example.com/bad", {}, "json"))
    assert status == 400 and data == {"error": "bad request"}

    text, status = asyncio.run(sch.httpx_post("https://example.com/bad", {}, "text"))
    assert status == 400 and text == "Bad Request"


def test_httpx_get_post_exception(monkeypatch, sch):
    class FailingAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, params=None):
            raise httpx.RequestError("boom", request=None)

        async def post(self, url, data=None, headers=None, **_kwargs):
            raise httpx.RequestError("boom", request=None)

    monkeypatch.setattr(sch.httpx, "AsyncClient", lambda *a, **k: FailingAsyncClient())

    data, status = asyncio.run(sch.httpx_get("https://example.com", {}, "json"))
    assert status == 0 and data == {}

    text, status = asyncio.run(sch.httpx_get("https://example.com", {}, "text"))
    assert status == 0 and text == ""

    data, status = asyncio.run(sch.httpx_post("https://example.com", {}, "json"))
    assert status == 0 and data == {}

    text, status = asyncio.run(sch.httpx_post("https://example.com", {}, "text"))
    assert status == 0 and text == ""


def test_is_visible_quadrants_and_boundaries(fresh_config, monkeypatch, sch):
    # Build a minimal object that mimics astropy's transform_to result
    class FakeAltAz:
        def __init__(self, az_deg: float, alt_deg: float):
            import astropy.units as u

            self.az = az_deg * u.deg
            self.alt = alt_deg * u.deg

    class FakeCoord:
        def __init__(self, az_deg: float, alt_deg: float):
            self._az = az_deg
            self._alt = alt_deg

        def transform_to(self, frame):  # frame is unused; duck-typed
            return FakeAltAz(self._az, self._alt)

    # East (45-135)
    assert (
        bool(sch.is_visible(fresh_config, FakeCoord(90.0, 30.0), sch.Time.now()))
        is True
    )
    # South (135-225)
    assert (
        bool(sch.is_visible(fresh_config, FakeCoord(180.0, 30.0), sch.Time.now()))
        is True
    )
    # West (225-315)
    assert (
        bool(sch.is_visible(fresh_config, FakeCoord(270.0, 30.0), sch.Time.now()))
        is True
    )
    # North (wrap-around 315-360 or 0-45) now handled inclusively
    assert (
        bool(sch.is_visible(fresh_config, FakeCoord(0.0, 30.0), sch.Time.now())) is True
    )

    # Boundary azimuths should be visible when altitude equals threshold (10 deg)
    assert (
        bool(sch.is_visible(fresh_config, FakeCoord(45.0, 10.0), sch.Time.now()))
        is True
    )  # East boundary
    assert (
        bool(sch.is_visible(fresh_config, FakeCoord(135.0, 10.0), sch.Time.now()))
        is True
    )  # South boundary
    assert (
        bool(sch.is_visible(fresh_config, FakeCoord(225.0, 10.0), sch.Time.now()))
        is True
    )  # West boundary
    assert (
        bool(sch.is_visible(fresh_config, FakeCoord(315.0, 10.0), sch.Time.now()))
        is True
    )  # North boundary

    # Below threshold altitude should be not visible even in correct sector
    assert (
        bool(sch.is_visible(fresh_config, FakeCoord(90.0, 9.9), sch.Time.now()))
        is False
    )


def test_observing_target_list_scraper_parses_table(monkeypatch, sch):
    # Construct HTML with at least 4 tables, the fourth containing headers and a row
    html = (
        b"<html><body>"
        b"<table></table>"  # 0
        b"<table></table>"  # 1
        b"<table></table>"  # 2
        b"<table>"  # 3
        b"  <tr><th>Designation</th><th>Mag</th><th>t2</th><th>t3</th><th>Time</th><th>RA</th><th>Dec</th><th>Alt</th></tr>"
        b"  <tr><td>2025 AB</td><td>18.2</td><td>x</td><td>y</td><td>2025-01-01T00:00z</td><td>12 00 00</td><td>-30 00 00</td><td>45</td></tr>"
        b"</table>"
        b"</body></html>"
    )

    monkeypatch.setattr(
        sch.requests,
        "post",
        lambda url, data=None, params=None, **kwargs: FakeRequestsSuccessResponse(html),
    )

    data = sch.observing_target_list_scraper("https://mpc", {"k": "v"})

    # Expect at least one non-empty row present
    assert any(data), "Expected at least one parsed row"
    assert [
        "2025 AB",
        "18.2",
        "x",
        "y",
        "2025-01-01T00:00z",
        "12 00 00",
        "-30 00 00",
        "45",
    ] in data


def test_observing_target_list_filters_and_formats(monkeypatch, fresh_config, sch):
    # Provide a deterministic scraper output
    rows: list[list[str]] = [
        [
            "2025 AB",
            "18.2",
            "x",
            "y",
            "2025-01-01T00:00z",
            "12 00 00",
            "-30 00 00",
            "45",
        ]
    ]
    monkeypatch.setattr(sch, "observing_target_list_scraper", lambda url, payload: rows)
    monkeypatch.setattr(sch, "is_visible", lambda config, coord, t: True)

    table = sch.observing_target_list(fresh_config, {"dummy": "1"})

    assert len(table) == 1
    assert table[0]["Designation"] == "2025 AB"
    assert table[0]["RA"] == sch.skycoord_format("12 00 00", "ra")
    assert table[0]["Dec"] == sch.skycoord_format("-30 00 00", "dec")
    assert table[0]["Time"] == "2025-01-01T00:00"


def test_mpc_whatsup_table_cell_calendar_with_ut_paren(sch):
    t = sch.mpc_whatsup_table_cell_to_time("2026 5 24.559 (13:25 UTC)")
    assert "2026-05-24 13:25:00" in t.iso


def test_mpc_whatsup_table_legacy_iso_string(sch):
    t = sch.mpc_whatsup_table_cell_to_time("2025-01-01T00:00z")
    assert t.iso.startswith("2025-01-01 00:00:00")


def test_observing_target_list_includes_new_mpc_time_strings(
    monkeypatch, fresh_config, sch
):
    rows: list[list[str]] = [
        [
            "(4)",
            "8.3",
            "59",
            "160",
            "2026 5 24.500 (12:00 UT)",
            "00 23 41.2",
            "-03 12 22",
            "13.5",
        ],
    ]
    monkeypatch.setattr(sch, "observing_target_list_scraper", lambda url, payload: rows)
    monkeypatch.setattr(sch, "is_visible", lambda config, coord, t: True)

    table = sch.observing_target_list(fresh_config, {"dummy": "1"})
    assert len(table) == 1


def test_observing_target_list_scraper_no_tables(monkeypatch, sch):
    html = b"<html><body><p>No tables here</p></body></html>"
    monkeypatch.setattr(
        sch.requests,
        "post",
        lambda url, data=None, params=None, **kwargs: FakeRequestsSuccessResponse(html),
    )

    data = sch.observing_target_list_scraper("https://mpc", {"k": "v"})
    assert data == []


def test_observing_target_list_scraper_tables_without_expected_headers(
    monkeypatch, sch
):
    # Two tables, but none has the expected headers; also fewer than 4 tables
    html = (
        b"<html><body>"
        b"<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>"
        b"<table><tr><th>C</th><th>D</th></tr><tr><td>3</td><td>4</td></tr></table>"
        b"</body></html>"
    )
    monkeypatch.setattr(
        sch.requests,
        "post",
        lambda url, data=None, params=None, **kwargs: FakeRequestsSuccessResponse(html),
    )

    data = sch.observing_target_list_scraper("https://mpc", {"k": "v"})
    assert data == []


def test_observing_target_list_skips_malformed_rows(monkeypatch, fresh_config, sch):
    # Row with fewer than 8 fields and one with bad time should be skipped
    rows: list[list[str]] = [
        ["2025 AB", "18.2"],  # malformed short row
        [
            "2025 AC",
            "18.2",
            "x",
            "y",
            "bad-time-value",
            "12 00 00",
            "-30 00 00",
            "45",
        ],
    ]
    monkeypatch.setattr(sch, "observing_target_list_scraper", lambda url, payload: rows)
    monkeypatch.setattr(sch, "is_visible", lambda config, coord, t: True)

    table = sch.observing_target_list(fresh_config, {"dummy": "1"})
    assert len(table) == 0


def test_neocp_confirmation_returns_table_even_when_filtering_all(
    monkeypatch, fresh_config, sch
):
    # Short-circuit the risky branch by ensuring first condition fails (Score <= min_score)
    sample = [
        {
            "Temp_Desig": "P10abcd",
            "R.A.": "10.0",
            "Decl.": "-5.0",
            "Score": 1,  # will be <= min_score
            "V": "22.1",
            "NObs": "3",
            "Arc": "0.1",
            "Not_Seen_dys": "1.2",
        }
    ]

    async def fake_httpx_get(url: str, payload: dict[str, Any], return_type: str):
        return [sample, 200]

    async def fake_get_neocp_ephemeris(config, object_names):
        return {
            "P10abcd": [
                "",
                "",
                "",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
            ]
        }

    monkeypatch.setattr(sch, "httpx_get", fake_httpx_get)
    monkeypatch.setattr(sch, "get_neocp_ephemeris", fake_get_neocp_ephemeris)
    monkeypatch.setattr(sch, "is_visible", lambda c, coord, t: True)

    tbl = sch.neocp_confirmation(
        fresh_config, min_score=100, max_magnitude=20, min_altitude=20
    )
    # Should return a QTable with the right columns and zero rows
    assert list(tbl.colnames) == [
        "Temp_Desig",
        "Score",
        "R.A.",
        "Decl",
        "Alt",
        "V",
        'Velocity "/min',
        "Direction",
        "NObs",
        "Arc",
        "Not_seen",
    ]
    assert len(tbl) == 0


def test_neocp_confirmation_includes_valid_object(monkeypatch, fresh_config, sch):
    # A sample entry that should pass all filters
    sample = [
        {
            "Temp_Desig": "X12345",
            "R.A.": "10.0",  # degrees
            "Decl.": "30.0",  # degrees
            "Score": 85,
            "V": "18.5",
            "NObs": "4",
            "Arc": "0.5",
            "Not_Seen_dys": "0.0",
        }
    ]

    async def fake_httpx_get(url, payload, return_type):
        return [sample, 200]

    async def fake_get_neocp_ephemeris(config, object_names):
        return {
            "X12345": [
                "",
                "",
                "",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "1.5",
                "45.0",
            ]
        }

    # Ensure visibility gate passes deterministically
    monkeypatch.setattr(sch, "httpx_get", fake_httpx_get)
    monkeypatch.setattr(sch, "get_neocp_ephemeris", fake_get_neocp_ephemeris)
    monkeypatch.setattr(sch, "is_visible", lambda c, coord, t: True)

    # Altitude depends on current UTC; allow slightly below-horizon so the row is included
    # regardless of time-of-day.
    tbl = sch.neocp_confirmation(
        fresh_config, min_score=50, max_magnitude=19.0, min_altitude=-30
    )

    assert len(tbl) == 1
    row = tbl[0]
    assert row["Temp_Desig"] == "X12345"
    assert int(row["Score"]) == 85
    assert float(row["V"]) == 18.5
    assert int(row["NObs"]) == 4
    assert float(row['Velocity "/min']) == 1.5
    assert float(row["Direction"]) == 45.0


def test_neocp_confirmation_raises_when_event_loop_running(
    monkeypatch, fresh_config, sch
):
    sample = [
        {
            "Temp_Desig": "X12345",
            "R.A.": "10.0",
            "Decl.": "30.0",
            "Score": 85,
            "V": "18.5",
            "NObs": "4",
            "Arc": "0.5",
            "Not_Seen_dys": "0.0",
        }
    ]

    async def fake_httpx_get(url, payload, return_type):
        return [sample, 200]

    async def fake_get_neocp_ephemeris(config, object_names):
        return {
            "X12345": [
                "",
                "",
                "",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "1.5",
                "45.0",
            ]
        }

    monkeypatch.setattr(sch, "httpx_get", fake_httpx_get)
    monkeypatch.setattr(sch, "get_neocp_ephemeris", fake_get_neocp_ephemeris)
    monkeypatch.setattr(sch, "is_visible", lambda c, coord, t: True)

    async def call_sync_from_async():
        sch.neocp_confirmation(
            fresh_config, min_score=50, max_magnitude=19.0, min_altitude=0
        )

    with pytest.raises(RuntimeError, match="async_neocp_confirmation"):
        asyncio.run(call_sync_from_async())


def test_async_neocp_confirmation_matches_sync_wrapper(monkeypatch, fresh_config, sch):
    sample = [
        {
            "Temp_Desig": "X12345",
            "R.A.": "10.0",
            "Decl.": "30.0",
            "Score": 85,
            "V": "18.5",
            "NObs": "4",
            "Arc": "0.5",
            "Not_Seen_dys": "0.0",
        }
    ]

    async def fake_httpx_get(url, payload, return_type):
        return [sample, 200]

    async def fake_get_neocp_ephemeris(config, object_names):
        return {
            "X12345": [
                "",
                "",
                "",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "1.5",
                "45.0",
            ]
        }

    monkeypatch.setattr(sch, "httpx_get", fake_httpx_get)
    monkeypatch.setattr(sch, "get_neocp_ephemeris", fake_get_neocp_ephemeris)
    monkeypatch.setattr(sch, "is_visible", lambda c, coord, t: True)

    sync_tbl = sch.neocp_confirmation(
        fresh_config, min_score=50, max_magnitude=19.0, min_altitude=-30
    )
    async_tbl = asyncio.run(
        sch.async_neocp_confirmation(
            fresh_config, min_score=50, max_magnitude=19.0, min_altitude=-30
        )
    )

    assert len(sync_tbl) == len(async_tbl) == 1
    assert sync_tbl[0]["Temp_Desig"] == async_tbl[0]["Temp_Desig"]
    assert float(sync_tbl[0]['Velocity "/min']) == float(async_tbl[0]['Velocity "/min'])


def test_twilight_times(monkeypatch, fresh_config, sch):
    class FakeObserver:
        def __init__(self, name: str, location: Any):
            self.name = name
            self.location = location

        # Return recognizable sentinel values
        def twilight_morning_astronomical(self, t, which="next"):
            return "AM_A"

        def twilight_evening_astronomical(self, t, which="next"):
            return "PM_A"

        def twilight_morning_civil(self, t, which="next"):
            return "AM_C"

        def twilight_evening_civil(self, t, which="next"):
            return "PM_C"

        def twilight_morning_nautical(self, t, which="next"):
            return "AM_N"

        def twilight_evening_nautical(self, t, which="next"):
            return "PM_N"

    monkeypatch.setattr(sch, "Observer", FakeObserver)

    result = sch.twilight_times(fresh_config)
    assert result == {
        "AstroM": "AM_A",
        "AstroE": "PM_A",
        "CivilM": "AM_C",
        "CivilE": "PM_C",
        "NautiM": "AM_N",
        "NautiE": "PM_N",
    }


def test_sun_moon_ephemeris(monkeypatch, fresh_config, sch):
    class FakeObserver:
        def __init__(self, name: str, location: Any):
            pass

        def sun_rise_time(self, t, which="next"):
            return "Sunrise"

        def sun_set_time(self, t, which="next"):
            return "Sunset"

        def moon_rise_time(self, t, which="next"):
            return "Moonrise"

        def moon_set_time(self, t, which="next"):
            return "Moonset"

        def moon_illumination(self, t):
            return 0.42

    monkeypatch.setattr(sch, "Observer", FakeObserver)

    result = sch.sun_moon_ephemeris(fresh_config)
    assert result == {
        "Sunrise": "Sunrise",
        "Sunset": "Sunset",
        "Moonrise": "Moonrise",
        "Moonset": "Moonset",
        "MoonIll": 0.42,
    }


def test_object_ephemeris_monkeypatched_mpc(monkeypatch, fresh_config, sch):
    calls: dict[str, Any] = {}

    def fake_get_ephemeris(name: str, location: Any, step: Any, number: int):
        calls["step"] = step
        # Minimal table carrying expected columns
        from astropy.table import QTable

        return QTable(
            {
                "Date": ["t1", "t2"],
                "RA": ["1h", "2h"],
                "Dec": ["+1d", "+2d"],
                "Elongation": [10.0, 20.0],
                "V": [18.0, 19.0],
                "Altitude": [30.0, 40.0],
                "Proper motion": [0.1, 0.2],
                "Direction": ["E", "W"],
            }
        )

    monkeypatch.setattr(sch.MPC, "get_ephemeris", fake_get_ephemeris)

    # Check different stepping codes
    t = sch.object_ephemeris(fresh_config, "Ceres", stepping="m")
    assert len(t) == 2

    t = sch.object_ephemeris(fresh_config, "Ceres", stepping="h")
    assert len(t) == 2

    t = sch.object_ephemeris(fresh_config, "Ceres", stepping="d")
    assert len(t) == 2

    t = sch.object_ephemeris(fresh_config, "Ceres", stepping="w")
    assert len(t) == 2


def test_object_ephemeris_invalid_stepping_defaults_to_hour(
    monkeypatch, fresh_config, sch
):
    calls: dict[str, Any] = {}

    def fake_get_ephemeris(name: str, location: Any, step: Any, number: int):
        calls["step"] = step
        from astropy.table import QTable

        # Single-row minimal table carrying expected columns
        return QTable(
            {
                "Date": ["t1"],
                "RA": ["1h"],
                "Dec": ["+1d"],
                "Elongation": [10.0],
                "V": [18.0],
                "Altitude": [30.0],
                "Proper motion": [0.1],
                "Direction": ["E"],
            }
        )

    monkeypatch.setattr(sch.MPC, "get_ephemeris", fake_get_ephemeris)

    # Use an unsupported stepping code; implementation should default to '1h'
    t = sch.object_ephemeris(fresh_config, "Ceres", stepping="x")
    assert len(t) == 1
    assert calls["step"] == "1h"


def test_neocp_confirmation_skips_zero_velocity_objects(monkeypatch, fresh_config, sch):
    """Test that objects with zero velocity are skipped"""
    sample = [
        {
            "Temp_Desig": "ZERO123",
            "R.A.": "10.0",
            "Decl.": "30.0",
            "Score": 85,
            "V": "18.5",
            "NObs": "4",
            "Arc": "0.5",
            "Not_Seen_dys": "0.0",
        }
    ]

    async def fake_httpx_get(url, payload, return_type):
        return [sample, 200]

    async def fake_get_neocp_ephemeris(config, object_names):
        # Return zero velocity which should cause the object to be skipped
        return {
            "ZERO123": [
                "",
                "",
                "",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
                "0.0",
            ]
        }

    monkeypatch.setattr(sch, "httpx_get", fake_httpx_get)
    monkeypatch.setattr(sch, "get_neocp_ephemeris", fake_get_neocp_ephemeris)
    monkeypatch.setattr(sch, "is_visible", lambda c, coord, t: True)

    tbl = sch.neocp_confirmation(
        fresh_config, min_score=50, max_magnitude=19.0, min_altitude=0
    )

    # Should return empty table because zero velocity objects are skipped
    assert len(tbl) == 0


def test_neocp_confirmation_handles_missing_ephemeris_data(
    monkeypatch, fresh_config, sch
):
    """Test that missing ephemeris data is handled gracefully"""
    sample = [
        {
            "Temp_Desig": "MISSING123",
            "R.A.": "10.0",
            "Decl.": "30.0",
            "Score": 85,
            "V": "18.5",
            "NObs": "4",
            "Arc": "0.5",
            "Not_Seen_dys": "0.0",
        }
    ]

    async def fake_httpx_get(url, payload, return_type):
        return [sample, 200]

    async def fake_get_neocp_ephemeris(config, object_names):
        # Return empty dict or object with insufficient data
        return {}

    monkeypatch.setattr(sch, "httpx_get", fake_httpx_get)
    monkeypatch.setattr(sch, "get_neocp_ephemeris", fake_get_neocp_ephemeris)
    monkeypatch.setattr(sch, "is_visible", lambda c, coord, t: True)

    tbl = sch.neocp_confirmation(
        fresh_config, min_score=50, max_magnitude=19.0, min_altitude=0
    )

    # Should return empty table because missing ephemeris data results in zero velocity
    assert len(tbl) == 0


def _observatory_config(**options: str) -> ConfigParser:
    """A ConfigParser whose ``[Observatory]`` holds exactly *options*."""
    config = ConfigParser()
    config["Observatory"] = dict(options)
    return config


@pytest.mark.parametrize(
    "options, expected",
    [
        # A real observatory code always wins, whatever the coordinates say.
        (
            {"mpc_code": "589", "latitude": "45.6", "longitude": "9.2"},
            "Parallax=1&obscode=589&long=45.6&lat=9.2&alt=0.0",
        ),
        (
            {"mpc_code": "589", "latitude": "0.0", "longitude": "0.0"},
            "Parallax=1&obscode=589&long=0.0&lat=0.0&alt=0.0",
        ),
        # Placeholder codes with real coordinates defer to the coordinates.
        (
            {
                "mpc_code": "500",
                "latitude": "45.6",
                "longitude": "9.2",
                "altitude": "120",
            },
            "Parallax=2&obscode=500&long=45.6&lat=9.2&alt=120.0",
        ),
        (
            {"mpc_code": "XXX", "latitude": "45.6", "longitude": "9.2"},
            "Parallax=2&obscode=XXX&long=45.6&lat=9.2&alt=0.0",
        ),
        (
            {"mpc_code": "0", "latitude": "-33.86", "longitude": "-70.6"},
            "Parallax=2&obscode=0&long=-33.86&lat=-70.6&alt=0.0",
        ),
        (
            {"mpc_code": "", "latitude": "45.6", "longitude": "9.2"},
            "Parallax=2&obscode=&long=45.6&lat=9.2&alt=0.0",
        ),
        # Placeholder codes without coordinates mean the geocenter, not a
        # fictitious site at 0 E / 0 N.
        (
            {"mpc_code": "500", "latitude": "0.0", "longitude": "0.0"},
            "Parallax=0&obscode=500&long=0.0&lat=0.0&alt=0.0",
        ),
        (
            {"mpc_code": "", "latitude": "0.0", "longitude": "0.0"},
            "Parallax=0&obscode=&long=0.0&lat=0.0&alt=0.0",
        ),
        # Altitude alone is not a site: 0 E / 0 N stays geocentric.
        (
            {
                "mpc_code": "500",
                "latitude": "0.0",
                "longitude": "0.0",
                "altitude": "120",
            },
            "Parallax=0&obscode=500&long=0.0&lat=0.0&alt=120.0",
        ),
        # The CGI validates long/lat for every Parallax value, so unparsable or
        # absent coordinates must still produce a valid request.
        (
            {"mpc_code": "500", "latitude": "abc", "longitude": "xyz"},
            "Parallax=0&obscode=500&long=0.0&lat=0.0&alt=0.0",
        ),
        (
            {"mpc_code": "589", "latitude": "abc", "longitude": "xyz"},
            "Parallax=1&obscode=589&long=0.0&lat=0.0&alt=0.0",
        ),
        ({"mpc_code": "500"}, "Parallax=0&obscode=500&long=0.0&lat=0.0&alt=0.0"),
        (
            {
                "mpc_code": "500",
                "latitude": "45.6",
                "longitude": "9.2",
                "altitude": "sea level",
            },
            "Parallax=2&obscode=500&long=45.6&lat=9.2&alt=0.0",
        ),
        # Surrounding whitespace in a hand-edited INI must not break the request.
        (
            {"mpc_code": "  589  ", "latitude": "45.6", "longitude": "9.2"},
            "Parallax=1&obscode=589&long=45.6&lat=9.2&alt=0.0",
        ),
    ],
)
def test_neocp_viewing_point_fields(sch, options, expected):
    """The MPC viewing point follows the code, then the coordinates, then the geocenter."""
    assert sch._neocp_viewing_point_fields(_observatory_config(**options)) == expected


def test_get_neocp_ephemeris_sends_viewing_point_fields(monkeypatch, sch):
    """The selected viewing point reaches the POST body verbatim."""
    sent: dict[str, Any] = {}

    class MockResponse:
        text = ""

    class MockAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, *args, **kwargs):
            sent.update(kwargs)
            return MockResponse()

    monkeypatch.setattr(sch.httpx, "AsyncClient", lambda *a, **k: MockAsyncClient())

    config = _observatory_config(
        mpc_code="XXX", latitude="45.6", longitude="9.2", altitude="120"
    )
    asyncio.run(sch.get_neocp_ephemeris(config, ["TEST123"]))

    body = sent["content"]
    assert "Parallax=2&obscode=XXX&long=45.6&lat=9.2&alt=120.0" in body
    assert "obj=TEST123" in body


def test_get_neocp_ephemeris_parses_response_correctly(monkeypatch, fresh_config, sch):
    """Test the regex parsing functionality in get_neocp_ephemeris"""
    sample_html = """
    <html>
    <body>
        <b>TEST123</b>
        <pre>
        Line 1: header
        Line 2: intermediate
        Line 3: data1 data2 data3 data4 data5 data6 data7 data8 data9 data10 data11 data12 data13 data14
        </pre>
        <b>TEST456</b>
        <pre>
        Line 1: header2
        Line 2: intermediate2
        Line 3: val1 val2 val3 val4 val5 val6 val7 val8 val9 val10 val11 val12 val13 val14
        </pre>
    </body>
    </html>
    """

    class MockResponse:
        def __init__(self, text):
            self.text = text

    class MockAsyncClient:
        def __init__(self, text):
            self._text = text

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, *args, **kwargs):
            return MockResponse(self._text)

    def make_client(*args, **kwargs):
        return MockAsyncClient(sample_html)

    monkeypatch.setattr(sch.httpx, "AsyncClient", make_client)

    result = asyncio.run(sch.get_neocp_ephemeris(fresh_config, ["TEST123", "TEST456"]))

    # Should return a dictionary with parsed data
    assert isinstance(result, dict)
    assert "TEST123" in result
    assert "TEST456" in result

    # Check that the data arrays have the expected structure
    assert len(result["TEST123"]) >= 14  # Should have at least 14 elements
    assert len(result["TEST456"]) >= 14


def test_get_neocp_ephemeris_handles_insufficient_data(monkeypatch, fresh_config, sch):
    """Test that insufficient data in response is handled correctly"""
    sample_html = """
    <html>
    <body>
        <b>SHORT123</b>
        <pre>
        Line 1: header
        Line 2: data1 data2
        </pre>
    </body>
    </html>
    """

    class MockResponse:
        def __init__(self, text):
            self.text = text

    class MockAsyncClient:
        def __init__(self, text):
            self._text = text

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, *args, **kwargs):
            return MockResponse(self._text)

    def make_client(*args, **kwargs):
        return MockAsyncClient(sample_html)

    monkeypatch.setattr(sch.httpx, "AsyncClient", make_client)

    result = asyncio.run(sch.get_neocp_ephemeris(fresh_config, ["SHORT123"]))

    # Should return empty dict because insufficient data is skipped
    assert result == {}


class FakeWeatherJsonResponse:
    """Minimal ``requests.get`` result for ``weather_forecast_raw`` mocks."""

    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(response=None)

    def json(self) -> Any:
        return self._payload


def test_weather_forecast_raw_success(monkeypatch, fresh_config, sch):
    payload = {"init": "2026092500", "dataseries": [{"timepoint": 3, "cloudcover": 1}]}
    monkeypatch.setattr(
        sch.requests,
        "get",
        lambda url, params=None, **kwargs: FakeWeatherJsonResponse(payload),
    )
    assert sch.weather_forecast_raw(fresh_config) == payload


def test_weather_forecast_raw_request_failure(monkeypatch, fresh_config, sch):
    def boom(url, params=None, **kwargs):
        raise requests.RequestException("net down")

    monkeypatch.setattr(sch.requests, "get", boom)
    assert sch.weather_forecast_raw(fresh_config) == {}


def test_weather_forecast_raw_non_json(monkeypatch, fresh_config, sch):
    class NonJsonResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> Any:
            raise ValueError("no json")

    monkeypatch.setattr(
        sch.requests, "get", lambda url, params=None, **kwargs: NonJsonResponse()
    )
    assert sch.weather_forecast_raw(fresh_config) == {}


def test_weather_forecast_report_on_empty_raw(monkeypatch, fresh_config, sch):
    monkeypatch.setattr(sch, "weather_forecast_raw", lambda config, product="astro": {})
    assert (
        sch.weather_forecast_report(fresh_config)
        == "Weather forecast request failed or the response was not valid JSON."
    )


def test_astronomical_night_uses_local_solar_noon(monkeypatch, fresh_config, sch):
    calls: dict[str, Any] = {}

    class FakeObserver:
        def __init__(self, name: str, location: Any):
            self.name = name
            self.location = location

        def twilight_evening_astronomical(self, t, which="next"):
            calls["evening_ref"] = t
            return sch.Time("2026-09-26 17:30:00")

        def twilight_morning_astronomical(self, t, which="next"):
            calls["morning_ref"] = t
            return sch.Time("2026-09-27 04:30:00")

    monkeypatch.setattr(sch, "Observer", FakeObserver)

    # fresh_config longitude == 9.0 => local solar noon at 11:24 UTC
    evening, morning = sch.astronomical_night(
        fresh_config, sch.datetime.date(2026, 9, 26)
    )
    assert str(evening) == "2026-09-26 17:30:00.000"
    assert str(morning) == "2026-09-27 04:30:00.000"
    assert calls["evening_ref"].iso.startswith("2026-09-26 11:24")
    assert calls["morning_ref"].iso.startswith("2026-09-26 11:24")


def _planner_tp(hours: int, cloud: int, seeing: int, transp: int, prec: str = "none"):
    """One 7Timer ``astro`` timepoint, *hours* after the forecast init."""

    return {
        "timepoint": hours,
        "cloudcover": cloud,
        "seeing": seeing,
        "transparency": transp,
        "prec_type": prec,
    }


def _planner_three_night_forecast() -> list[dict[str, Any]]:
    """3-hourly 7Timer-style forecast spanning three nights (26/27 clear, 28 rainy)."""

    return [
        # night of 2026-09-26, window [26 17:30, 27 04:30)
        _planner_tp(18, 1, 1, 8),
        _planner_tp(21, 1, 1, 8),
        _planner_tp(24, 1, 1, 8),
        _planner_tp(27, 1, 1, 8),
        # daytime 27
        _planner_tp(30, 1, 1, 8),
        _planner_tp(33, 1, 1, 8),
        _planner_tp(36, 1, 1, 8),
        _planner_tp(39, 1, 1, 8),
        # night of 2026-09-27, window [27 17:30, 28 04:30)
        _planner_tp(42, 5, 4, 4),
        _planner_tp(45, 5, 4, 4),
        _planner_tp(48, 5, 4, 4),
        _planner_tp(51, 5, 4, 4),
        # daytime 28
        _planner_tp(54, 5, 4, 4),
        _planner_tp(57, 5, 4, 4),
        _planner_tp(60, 5, 4, 4),
        _planner_tp(63, 5, 4, 4),
        # night of 2026-09-28, window [28 17:30, 29 04:30) -> rainy
        _planner_tp(66, 1, 1, 8, prec="rain"),
        _planner_tp(69, 1, 1, 8, prec="rain"),
    ]


def _planner_mock_fakes(sch):
    """Return ``(raw, astronomical_night, FakeObserver)`` for the 3-night forecast."""

    def fake_raw(config: ConfigParser, product: str = "astro") -> dict[str, Any]:
        return {"init": "2026092600", "dataseries": _planner_three_night_forecast()}

    def fake_astronomical_night(config: ConfigParser, date: Any):
        windows = {
            sch.datetime.date(2026, 9, 26): (
                "2026-09-26 17:30:00",
                "2026-09-27 04:30:00",
            ),
            sch.datetime.date(2026, 9, 27): (
                "2026-09-27 17:30:00",
                "2026-09-28 04:30:00",
            ),
            sch.datetime.date(2026, 9, 28): (
                "2026-09-28 17:30:00",
                "2026-09-29 04:30:00",
            ),
        }
        start, end = windows[date]
        return (sch.Time(start), sch.Time(end))

    class FakeObserver:
        def __init__(self, name: str, location: Any):
            self.name = name
            self.location = location

        def moon_illumination(self, t):
            return 0.1

    return fake_raw, fake_astronomical_night, FakeObserver


def test_best_nights_ranks_nights_and_excludes_precipitation(
    monkeypatch, fresh_config, sch
):
    raw, astro, observer_cls = _planner_mock_fakes(sch)
    monkeypatch.setattr(sch, "weather_forecast_raw", raw)
    monkeypatch.setattr(sch, "astronomical_night", astro)
    monkeypatch.setattr(sch, "Observer", observer_cls)

    nights = sch.best_nights(fresh_config)

    # Rainy night (28) is excluded; clear night ranks above the cloudy one.
    assert [n["date"] for n in nights] == [
        sch.datetime.date(2026, 9, 26),
        sch.datetime.date(2026, 9, 27),
    ]
    assert nights[0]["score"] > nights[1]["score"]
    assert nights[0]["avg_cloud_pct"] == pytest.approx(3.0)
    assert nights[0]["moon_illum"] == pytest.approx(0.1)


def test_best_nights_respects_max_nights_override(monkeypatch, fresh_config, sch):
    raw, astro, observer_cls = _planner_mock_fakes(sch)
    monkeypatch.setattr(sch, "weather_forecast_raw", raw)
    monkeypatch.setattr(sch, "astronomical_night", astro)
    monkeypatch.setattr(sch, "Observer", observer_cls)

    nights = sch.best_nights(fresh_config, max_nights=1)
    assert len(nights) == 1
    assert nights[0]["date"] == sch.datetime.date(2026, 9, 26)


def test_best_nights_no_forecast(monkeypatch, fresh_config, sch):
    monkeypatch.setattr(sch, "weather_forecast_raw", lambda config, product="astro": {})
    assert sch.best_nights(fresh_config) == []
    assert "No weather forecast available." in sch.best_nights_report(fresh_config)


def test_best_nights_report_renders_ranked_table(monkeypatch, fresh_config, sch):
    raw, astro, observer_cls = _planner_mock_fakes(sch)
    monkeypatch.setattr(sch, "weather_forecast_raw", raw)
    monkeypatch.setattr(sch, "astronomical_night", astro)
    monkeypatch.setattr(sch, "Observer", observer_cls)

    report = sch.best_nights_report(fresh_config)
    assert "Best upcoming nights" in report
    assert "2026-09-26" in report
    assert "2026-09-27" in report
    assert "Score weights:" in report
    # The rainy night must not be listed.
    assert "2026-09-28" not in report


def test_planner_settings_fallback_and_normalization(monkeypatch, fresh_config, sch):
    settings = sch.planner_settings(fresh_config)
    assert settings["max_nights"] == sch.DEFAULT_PLANNER_MAX_NIGHTS
    assert settings["weights"]["cloud"] == pytest.approx(
        sch.DEFAULT_PLANNER_WEIGHTS["cloud"]
    )
    assert sum(settings["weights"].values()) == pytest.approx(1.0)

    fresh_config["Planner"] = {
        "max_nights": "3",
        "w_cloud": "1.0",
        "w_seeing": "1.0",
        "w_transparency": "1.0",
        "w_moon": "1.0",
    }
    settings = sch.planner_settings(fresh_config)
    assert settings["max_nights"] == 3
    assert all(v == pytest.approx(0.25) for v in settings["weights"].values())

    fresh_config["Planner"] = {
        "max_nights": "0",
        "w_cloud": "not-a-number",
        "w_seeing": "2.0",
        "w_transparency": "1.0",
        "w_moon": "1.0",
    }
    settings = sch.planner_settings(fresh_config)
    assert settings["max_nights"] == sch.DEFAULT_PLANNER_MAX_NIGHTS
    total = sch.DEFAULT_PLANNER_WEIGHTS["cloud"] + 2.0 + 1.0 + 1.0
    assert settings["weights"]["cloud"] == pytest.approx(
        sch.DEFAULT_PLANNER_WEIGHTS["cloud"] / total
    )


@pytest.mark.parametrize("bad_weight", ["-1.0", "-0.5", "nan", "inf", "-inf"])
def test_planner_settings_rejects_invalid_weights(bad_weight, fresh_config, sch):
    # A negative weight would invert a quality factor (e.g. a negative moon weight
    # would reward a brighter Moon) and let the score leave the 0-100 range;
    # non-finite values would poison the normalization. Both fall back.
    fresh_config["Planner"] = {
        "w_cloud": "1.0",
        "w_seeing": "1.0",
        "w_transparency": "1.0",
        "w_moon": bad_weight,
    }
    settings = sch.planner_settings(fresh_config)
    expected_total = 3.0 + sch.DEFAULT_PLANNER_WEIGHTS["moon"]
    assert settings["weights"]["moon"] == pytest.approx(
        sch.DEFAULT_PLANNER_WEIGHTS["moon"] / expected_total
    )
    assert all(value >= 0 for value in settings["weights"].values())
    assert sum(settings["weights"].values()) == pytest.approx(1.0)


def test_planner_settings_all_zero_weights_fall_back_to_defaults(fresh_config, sch):
    fresh_config["Planner"] = {
        "w_cloud": "0",
        "w_seeing": "0",
        "w_transparency": "0",
        "w_moon": "0",
    }
    settings = sch.planner_settings(fresh_config)
    assert settings["weights"] == pytest.approx(dict(sch.DEFAULT_PLANNER_WEIGHTS))


def test_best_nights_skips_non_mapping_forecast_items(monkeypatch, fresh_config, sch):
    # 7Timer occasionally returns a partially malformed series; a non-dict item
    # must be skipped instead of raising AttributeError in the Best Night screen.
    _, astro, observer_cls = _planner_mock_fakes(sch)

    def fake_raw(config: ConfigParser, product: str = "astro") -> dict[str, Any]:
        return {
            "init": "2026092600",
            "dataseries": [None, "oops", 42, ["nope"]]
            + _planner_three_night_forecast(),
        }

    monkeypatch.setattr(sch, "weather_forecast_raw", fake_raw)
    monkeypatch.setattr(sch, "astronomical_night", astro)
    monkeypatch.setattr(sch, "Observer", observer_cls)

    nights = sch.best_nights(fresh_config)
    assert [night["date"] for night in nights] == [
        sch.datetime.date(2026, 9, 26),
        sch.datetime.date(2026, 9, 27),
    ]


def test_best_nights_all_items_invalid(monkeypatch, fresh_config, sch):
    monkeypatch.setattr(
        sch,
        "weather_forecast_raw",
        lambda config, product="astro": {
            "init": "2026092600",
            "dataseries": [None, "oops", 42, [{"cloudcover": 1}]],
        },
    )
    assert sch.best_nights(fresh_config) == []
    assert "No weather forecast available." in sch.best_nights_report(fresh_config)


def test_planner_weight_options_match_the_known_factors(sch):
    # The editor inputs, the persistence layer and the scorer must agree on the
    # factor names, otherwise a saved weight would never be read back.
    import asteroidpy.configuration as configuration

    assert set(sch.PLANNER_WEIGHT_OPTIONS) == set(sch.DEFAULT_PLANNER_WEIGHTS)
    assert set(sch.PLANNER_WEIGHT_OPTIONS.values()) <= set(
        configuration.SECTION_DEFAULTS["Planner"]
    )
    assert configuration.PLANNER_WEIGHT_FACTORS == sch.PLANNER_WEIGHT_OPTIONS


def test_parse_planner_weights_normalizes_and_fills_defaults(fresh_config, sch):
    fresh_config["Planner"] = {"w_cloud": "4", "w_seeing": "2.5"}
    weights = sch.parse_planner_weights(fresh_config["Planner"])
    # Missing options fall back to the defaults, then all four are divided by
    # their sum: 4 + 2.5 + 0.15 + 0.2 = 6.85.
    assert weights == pytest.approx(
        {
            "cloud": 4 / 6.85,
            "seeing": 2.5 / 6.85,
            "transparency": 0.15 / 6.85,
            "moon": 0.2 / 6.85,
        }
    )
    assert sum(weights.values()) == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("raw", "reason", "options"),
    [
        ({"w_cloud": "abc"}, "not_a_number", {"w_cloud"}),
        ({"w_seeing": "-1"}, "out_of_range", {"w_seeing"}),
        ({"w_moon": "nan"}, "out_of_range", {"w_moon"}),
        ({"w_moon": "inf"}, "out_of_range", {"w_moon"}),
        (
            {"w_cloud": "0", "w_seeing": "0", "w_transparency": "0", "w_moon": "0"},
            "zero_sum",
            {"w_cloud", "w_seeing", "w_transparency", "w_moon"},
        ),
    ],
)
def test_parse_planner_weights_rejects_unusable_values(raw, reason, options, sch):
    with pytest.raises(sch.PlannerValueError) as excinfo:
        sch.parse_planner_weights(raw)
    assert excinfo.value.reason == reason
    assert set(excinfo.value.options) == options


def test_parse_planner_weights_names_every_offending_option(sch):
    with pytest.raises(sch.PlannerValueError) as excinfo:
        sch.parse_planner_weights({"w_cloud": "x", "w_moon": "-2"})
    assert set(excinfo.value.options) == {"w_cloud", "w_moon"}


@pytest.mark.parametrize("raw", ["0", "-1", "abc", "", "1.5", "2.0", None])
def test_parse_planner_max_nights_rejects_unusable_values(raw, sch):
    with pytest.raises(sch.PlannerValueError) as excinfo:
        sch.parse_planner_max_nights(raw)
    assert excinfo.value.reason in {"not_an_integer", "out_of_range"}
    assert excinfo.value.options == ("max_nights",)


@pytest.mark.parametrize(("raw", "expected"), [("1", 1), (" 12 ", 12), (30, 30)])
def test_parse_planner_max_nights_accepts_whole_numbers(raw, expected, sch):
    assert sch.parse_planner_max_nights(raw) == expected


def test_normalize_planner_weights_rejects_empty_sum(sch):
    with pytest.raises(sch.PlannerValueError) as excinfo:
        sch.normalize_planner_weights(dict.fromkeys(sch.DEFAULT_PLANNER_WEIGHTS, 0.0))
    assert excinfo.value.reason == "zero_sum"


def _planner_opposed_nights_forecast() -> list[dict[str, Any]]:
    """Forecast whose two usable nights trade places depending on the weights.

    Night 26 is overcast but transparent, night 27 is clear but hazy, and night 28
    is discarded for rain: a cloud-only ranking and a transparency-only ranking
    therefore disagree on the winner.
    """

    return [
        # night of 2026-09-26, window [26 17:30, 27 04:30)
        _planner_tp(18, 8, 4, 8),
        _planner_tp(21, 8, 4, 8),
        _planner_tp(24, 8, 4, 8),
        _planner_tp(27, 8, 4, 8),
        # daytime 27
        _planner_tp(30, 1, 1, 1),
        _planner_tp(33, 1, 1, 1),
        _planner_tp(36, 1, 1, 1),
        _planner_tp(39, 1, 1, 1),
        # night of 2026-09-27, window [27 17:30, 28 04:30)
        _planner_tp(42, 1, 1, 1),
        _planner_tp(45, 1, 1, 1),
        _planner_tp(48, 1, 1, 1),
        _planner_tp(51, 1, 1, 1),
        # daytime 28
        _planner_tp(54, 8, 4, 8),
        _planner_tp(57, 8, 4, 8),
        _planner_tp(60, 8, 4, 8),
        _planner_tp(63, 8, 4, 8),
        # night of 2026-09-28 -> rainy
        _planner_tp(66, 1, 1, 8, prec="rain"),
        _planner_tp(69, 1, 1, 8, prec="rain"),
    ]


def _patch_planner_forecast(monkeypatch, sch, series):
    """Wire the planner fakes around *series* and return the three fake helpers."""

    _raw, astro, observer_cls = _planner_mock_fakes(sch)
    monkeypatch.setattr(
        sch,
        "weather_forecast_raw",
        lambda config, product="astro": {"init": "2026092600", "dataseries": series},
    )
    monkeypatch.setattr(sch, "astronomical_night", astro)
    monkeypatch.setattr(sch, "Observer", observer_cls)
    return astro, observer_cls


def test_best_nights_weights_override_changes_the_ranking(
    monkeypatch, fresh_config, sch
):
    # The planner editor previews unsaved weights: passing them to best_nights
    # must be enough to change both the score and the order of the nights.
    _patch_planner_forecast(monkeypatch, sch, _planner_opposed_nights_forecast())
    clear = sch.datetime.date(2026, 9, 27)
    cloudy = sch.datetime.date(2026, 9, 26)

    cloud_only = sch.best_nights(
        fresh_config, weights={"cloud": 1, "seeing": 0, "transparency": 0, "moon": 0}
    )
    transparency_only = sch.best_nights(
        fresh_config, weights={"cloud": 0, "seeing": 0, "transparency": 1, "moon": 0}
    )
    assert cloud_only[0]["date"] == clear
    assert transparency_only[0]["date"] == cloudy
    # Weights are normalized, so a single factor scores on its own.
    assert cloud_only[0]["score"] == pytest.approx(100 * (1 - 3.0 / 100))
    assert transparency_only[0]["score"] == pytest.approx(100.0)


def test_best_nights_uses_configured_weights_by_default(monkeypatch, fresh_config, sch):
    _patch_planner_forecast(monkeypatch, sch, _planner_opposed_nights_forecast())
    fresh_config["Planner"] = {
        "max_nights": "2",
        "w_cloud": "0",
        "w_seeing": "0",
        "w_transparency": "1",
        "w_moon": "0",
    }
    nights = sch.best_nights(fresh_config)
    assert [night["date"] for night in nights] == [
        sch.datetime.date(2026, 9, 26),
        sch.datetime.date(2026, 9, 27),
    ]
    assert nights[0]["score"] == pytest.approx(100.0)


def test_best_nights_rejects_invalid_weights_override(fresh_config, sch):
    with pytest.raises(sch.PlannerValueError):
        sch.best_nights(
            fresh_config,
            weights={"cloud": -1, "seeing": 1, "transparency": 1, "moon": 1},
        )


def test_object_ephemeris_passes_the_requested_point_count(
    monkeypatch, fresh_config, sch
):
    seen: dict[str, int] = {}

    def fake_get_ephemeris(name: str, location: Any, step: Any, number: int):
        seen["number"] = number
        from astropy.table import QTable

        return QTable(
            {
                "Date": ["t1"],
                "RA": ["1h"],
                "Dec": ["+1d"],
                "Elongation": [10.0],
                "V": [18.0],
                "Altitude": [30.0],
                "Proper motion": [0.1],
                "Direction": ["E"],
            }
        )

    monkeypatch.setattr(sch.MPC, "get_ephemeris", fake_get_ephemeris)

    sch.object_ephemeris(fresh_config, "Ceres", stepping="h")
    assert seen["number"] == sch.DEFAULT_EPHEMERIS_POINTS

    sch.object_ephemeris(fresh_config, "Ceres", stepping="h", number=1)
    assert seen["number"] == 1

    sch.object_ephemeris(fresh_config, "Ceres", stepping="h", number="250")
    assert seen["number"] == 250


@pytest.mark.parametrize("number", [0, -1, 1.5, "abc", "", None, True, 10001])
def test_object_ephemeris_rejects_an_unusable_point_count(
    number, monkeypatch, fresh_config, sch
):
    def fake_get_ephemeris(name: str, location: Any, step: Any, number: int):
        raise AssertionError("the MPC must not be queried with an invalid count")

    monkeypatch.setattr(sch.MPC, "get_ephemeris", fake_get_ephemeris)

    with pytest.raises(ValueError):
        sch.object_ephemeris(fresh_config, "Ceres", stepping="h", number=number)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (1, 1),
        ("1", 1),
        (30, 30),
        (" 250 ", 250),
        (sch_max := 10000, sch_max),
    ],
)
def test_validated_ephemeris_points_accepts_the_documented_range(raw, expected, sch):
    assert sch.validated_ephemeris_points(raw) == expected


def _forecast_with_hours(timepoints: list[int], temp: Any = 12.3) -> dict[str, Any]:
    """Build a 7Timer ``astro`` payload with one timepoint per hour offset."""

    return {
        "init": "2026092600",
        "dataseries": [
            {
                "timepoint": hours,
                "cloudcover": 2,
                "seeing": 3,
                "transparency": 5,
                "lifted_index": -2,
                "temp2m": temp,
                "rh2m": 4,
                "wind10m": {"direction": 180, "speed": 5},
                "prec_type": "none",
            }
            for hours in timepoints
        ],
    }


def test_weather_forecast_report_horizon_limits_the_timepoints(
    monkeypatch, fresh_config, sch
):
    monkeypatch.setattr(
        sch,
        "weather_forecast_raw",
        lambda config, product="astro": _forecast_with_hours([0, 3, 6, 9, 72, 75]),
    )

    # Every kept row carries the temperature, so counting it counts the rows.
    assert sch.weather_forecast_report(fresh_config, hours=6).count("12.3 C") == 3
    assert sch.weather_forecast_report(fresh_config, hours=72).count("12.3 C") == 5
    # Without an explicit horizon the whole series is shown, as before.
    assert sch.weather_forecast_report(fresh_config).count("12.3 C") == 6


def test_weather_forecast_report_rejects_a_negative_horizon(fresh_config, sch):
    with pytest.raises(ValueError):
        sch.weather_forecast_report(fresh_config, hours=-3)


def test_weather_forecast_report_converts_the_temperature_unit(
    monkeypatch, fresh_config, sch
):
    monkeypatch.setattr(
        sch,
        "weather_forecast_raw",
        lambda config, product="astro": _forecast_with_hours([0]),
    )

    celsius = sch.weather_forecast_report(fresh_config, temperature_unit="C")
    fahrenheit = sch.weather_forecast_report(fresh_config, temperature_unit="F")
    assert "12.3 C" in celsius
    assert "54.1 F" in fahrenheit


def test_weather_forecast_report_skips_malformed_timepoints(
    monkeypatch, fresh_config, sch
):
    payload = _forecast_with_hours([0])
    payload["dataseries"] = [None, "nope", {"timepoint": 3, "temp2m": 5}] + payload[
        "dataseries"
    ]
    monkeypatch.setattr(
        sch, "weather_forecast_raw", lambda config, product="astro": payload
    )

    report = sch.weather_forecast_report(fresh_config)
    assert "5 C" in report


@pytest.mark.parametrize(
    ("celsius", "unit", "expected"),
    [
        (12.3, "C", "12.3 C"),
        (0, "C", "0 C"),
        (12.3, "F", "54.1 F"),
        (0, "F", "32.0 F"),
        (-40, "F", "-40.0 F"),
        (None, "C", "N/A"),
        (None, "F", "N/A"),
        ("oops", "F", "N/A"),
    ],
)
def test_weather_temperature(celsius, unit, expected, sch):
    assert sch.weather_temperature(celsius, unit) == expected


def _whatsup_page(token: str | None) -> bytes:
    """A What's Observable page with or without a Rails form token."""

    if token is None:
        return b"<html><body><form action='/whatsup/index'></form></body></html>"
    return (
        "<html><body><form>"
        f'<input type="hidden" name="authenticity_token" value="{token}">'
        "</form></body></html>"
    ).encode()


class _TokenResponse:
    def __init__(self, content: bytes, status_code: int = 200) -> None:
        self.content = content
        self.text = content.decode()
        self.status_code = status_code


def test_resolve_whatsup_authenticity_token_scrapes_the_form(monkeypatch, sch):
    monkeypatch.setattr(
        sch.requests,
        "get",
        lambda url, headers=None, timeout=None: _TokenResponse(_whatsup_page("fresh")),
    )
    assert sch.resolve_whatsup_authenticity_token() == "fresh"


def test_resolve_whatsup_authenticity_token_falls_back_to_the_csrf_meta(
    monkeypatch, sch
):
    page = b'<html><head><meta name="csrf-token" content="from-meta"></head></html>'
    monkeypatch.setattr(
        sch.requests,
        "get",
        lambda url, headers=None, timeout=None: _TokenResponse(page),
    )
    assert sch.resolve_whatsup_authenticity_token() == "from-meta"


def test_resolve_whatsup_authenticity_token_reports_a_page_without_token(
    monkeypatch, sch
):
    monkeypatch.setattr(
        sch.requests,
        "get",
        lambda url, headers=None, timeout=None: _TokenResponse(_whatsup_page(None)),
    )
    with pytest.raises(sch.DataSourceError) as raised:
        sch.resolve_whatsup_authenticity_token()
    assert raised.value.reason == sch.REASON_TOKEN_NOT_FOUND
    assert raised.value.source == sch.MPC_WHATSUP_SOURCE
    assert "MPC" in str(raised.value)


def test_resolve_whatsup_authenticity_token_reports_an_unexpected_status(
    monkeypatch, sch
):
    monkeypatch.setattr(
        sch.requests,
        "get",
        lambda url, headers=None, timeout=None: _TokenResponse(b"", status_code=503),
    )
    with pytest.raises(sch.DataSourceError) as raised:
        sch.resolve_whatsup_authenticity_token()
    assert raised.value.reason == sch.REASON_HTTP_STATUS
    assert "503" in str(raised.value)


@pytest.mark.parametrize(
    "error",
    [
        requests.Timeout("too slow"),
        requests.ConnectionError("no route"),
    ],
)
def test_resolve_whatsup_authenticity_token_reports_a_network_failure(
    monkeypatch, sch, error
):
    def boom(url, headers=None, timeout=None):
        raise error

    monkeypatch.setattr(sch.requests, "get", boom)
    with pytest.raises(sch.DataSourceError) as raised:
        sch.resolve_whatsup_authenticity_token()
    assert raised.value.reason == sch.REASON_NETWORK_ERROR
    assert isinstance(raised.value.__cause__, requests.RequestException)


def test_no_embedded_whatsup_token_is_left_in_the_sources(sch):
    # F6: the token must only ever come from the page, never from the source.
    source = pathlib.Path(sch.__file__).read_text()
    assert "W5eBzz" not in source
    assert "_MPC_WHATSUP_AUTH_TOKEN_FALLBACK" not in source


# --- Response cache (A1) -------------------------------------------------
#
# The acceptance criterion for the cache is blunt: a second, identical run must
# not reach the network. Each test below therefore counts the client calls
# instead of only checking the returned value.


class _Counter:
    """Count the calls made to a patched network client."""

    def __init__(self) -> None:
        self.calls = 0

    @property
    def count(self) -> int:
        return self.calls


def _counting_get(payload: Any, counter: _Counter):
    def fake_get(url, params=None, **kwargs):
        counter.calls += 1
        return FakeWeatherJsonResponse(payload)

    return fake_get


def test_second_weather_run_is_served_from_the_cache(monkeypatch, fresh_config, sch):
    payload = {"init": "2026092500", "dataseries": [{"timepoint": 3, "cloudcover": 1}]}
    counter = _Counter()
    monkeypatch.setattr(sch.requests, "get", _counting_get(payload, counter))

    assert sch.weather_forecast_raw(fresh_config) == payload
    assert sch.weather_forecast_raw(fresh_config) == payload
    assert counter.count == 1, "the second run must not re-query 7Timer"


def test_a_different_observatory_does_not_reuse_the_cached_forecast(
    monkeypatch, fresh_config, sch
):
    payload = {"init": "2026092500", "dataseries": []}
    counter = _Counter()
    monkeypatch.setattr(sch.requests, "get", _counting_get(payload, counter))

    sch.weather_forecast_raw(fresh_config)
    fresh_config["Observatory"]["latitude"] = "46.0"
    sch.weather_forecast_raw(fresh_config)

    assert counter.count == 2, "the cache key must include the observatory location"


def test_weather_falls_back_to_the_cached_forecast_when_the_network_dies(
    monkeypatch, fresh_config, sch
):
    payload = {"init": "2026092500", "dataseries": [{"timepoint": 3, "cloudcover": 1}]}
    counter = _Counter()
    monkeypatch.setattr(sch.requests, "get", _counting_get(payload, counter))
    assert sch.weather_forecast_raw(fresh_config) == payload

    def boom(url, params=None, **kwargs):
        raise requests.RequestException("net down")

    monkeypatch.setattr(sch.requests, "get", boom)
    # A dead network must not turn a usable forecast into "no data".
    assert sch.weather_forecast_raw(fresh_config) == payload


def test_second_whatsup_token_scrape_is_served_from_the_cache(monkeypatch, sch):
    html = (
        b"<html><body><form>"
        b'<input name="authenticity_token" value="tok-123" />'
        b"</form></body></html>"
    )
    counter = _Counter()

    class Response:
        content = html
        text = html.decode()
        status_code = 200

    def fake_get(url, headers=None, timeout=None):
        counter.calls += 1
        return Response()

    monkeypatch.setattr(sch.requests, "get", fake_get)

    assert sch.resolve_whatsup_authenticity_token() == "tok-123"
    assert sch.resolve_whatsup_authenticity_token() == "tok-123"
    assert counter.count == 1, "the form page must not be re-scraped"


def test_whatsup_token_falls_back_to_the_cached_one_on_a_network_failure(
    monkeypatch, sch
):
    html = (
        b"<html><body><form>"
        b'<input name="authenticity_token" value="tok-123" />'
        b"</form></body></html>"
    )

    class Response:
        content = html
        text = html.decode()
        status_code = 200

    monkeypatch.setattr(
        sch.requests, "get", lambda url, headers=None, timeout=None: Response()
    )
    assert sch.resolve_whatsup_authenticity_token() == "tok-123"

    def boom(url, headers=None, timeout=None):
        raise requests.ConnectionError("no route")

    monkeypatch.setattr(sch.requests, "get", boom)
    assert sch.resolve_whatsup_authenticity_token() == "tok-123"


def _write_stale_cache_entry(key: str, payload: Any) -> None:
    """Store *payload* as if it had been fetched well past any TTL."""

    sch = importlib.import_module("asteroidpy.scheduling")
    sch.cache.write(key, payload)
    path = sch.cache.entry_path(key)
    entry = json.loads(path.read_text(encoding="utf-8"))
    entry["stored_at"] = time.time() - 86400
    path.write_text(json.dumps(entry), encoding="utf-8")


def test_whatsup_token_is_not_served_from_cache_when_the_page_has_no_token(
    monkeypatch, sch
):
    # A page that lost its token is a change to report, not an outage to paper
    # over with a stale token (F6).
    class Response:
        content = b"<html><body><form></form></body></html>"
        text = "<html><body><form></form></body></html>"
        status_code = 200

    monkeypatch.setattr(
        sch.requests, "get", lambda url, headers=None, timeout=None: Response()
    )
    _write_stale_cache_entry(sch.cache.cache_key("whatsup-token"), "stale-token")

    with pytest.raises(sch.DataSourceError) as raised:
        sch.resolve_whatsup_authenticity_token()
    assert raised.value.reason == sch.REASON_TOKEN_NOT_FOUND


_TARGETS_HTML = (
    b"<html><body>"
    b"<table></table>"  # 0
    b"<table></table>"  # 1
    b"<table></table>"  # 2
    b"<table>"  # 3, the one the scraper prefers
    b"<tr><th>Designation</th><th>Mag</th><th>t2</th><th>t3</th>"
    b"<th>Time</th><th>RA</th><th>Dec</th><th>Alt</th></tr>"
    b"<tr><td>2026 AA</td><td>19.1</td><td>x</td><td>y</td>"
    b"<td>2026 9 27.5 (02:30 UT)</td><td>01 02 03.4</td>"
    b"<td>+05 06 07.8</td><td>42.0</td></tr>"
    b"</table>"
    b"</body></html>"
)


def test_second_target_list_query_is_served_from_the_cache(monkeypatch, sch):
    counter = _Counter()

    def fake_post(url, data=None, headers=None, timeout=None):
        counter.calls += 1
        return FakeRequestsSuccessResponse(_TARGETS_HTML)

    monkeypatch.setattr(sch.requests, "post", fake_post)

    payload = {"latitude": "45.0", "longitude": "9.0", "object_type": "mp"}
    first = sch.observing_target_list_scraper("https://mpc", payload)
    second = sch.observing_target_list_scraper("https://mpc", payload)

    assert first and first == second
    assert counter.count == 1, "the same query must not be POSTed twice"


def test_target_list_cache_key_ignores_the_authenticity_token(monkeypatch, sch):
    # The CSRF token is re-scraped on every run, so a key that included it would
    # never match and the cache would never be read.
    counter = _Counter()

    def fake_post(url, data=None, headers=None, timeout=None):
        counter.calls += 1
        return FakeRequestsSuccessResponse(_TARGETS_HTML)

    monkeypatch.setattr(sch.requests, "post", fake_post)

    first = sch.observing_target_list_scraper(
        "https://mpc", {"latitude": "45.0", "authenticity_token": "one"}
    )
    second = sch.observing_target_list_scraper(
        "https://mpc", {"latitude": "45.0", "authenticity_token": "two"}
    )

    assert first == second
    assert counter.count == 1


def test_target_list_cache_key_separates_different_queries(monkeypatch, sch):
    counter = _Counter()

    def fake_post(url, data=None, headers=None, timeout=None):
        counter.calls += 1
        return FakeRequestsSuccessResponse(_TARGETS_HTML)

    monkeypatch.setattr(sch.requests, "post", fake_post)

    sch.observing_target_list_scraper("https://mpc", {"latitude": "45.0"})
    sch.observing_target_list_scraper("https://mpc", {"latitude": "46.0"})

    assert counter.count == 2, "a different query must not reuse another entry"


def test_target_list_falls_back_to_cached_rows_on_a_network_failure(monkeypatch, sch):
    monkeypatch.setattr(
        sch.requests,
        "post",
        lambda url, data=None, headers=None, timeout=None: (
            FakeRequestsSuccessResponse(_TARGETS_HTML)
        ),
    )
    payload = {"latitude": "45.0"}
    first = sch.observing_target_list_scraper("https://mpc", payload)
    assert first

    def boom(url, data=None, headers=None, timeout=None):
        raise requests.ConnectionError("no route")

    monkeypatch.setattr(sch.requests, "post", boom)
    assert sch.observing_target_list_scraper("https://mpc", payload) == first


def test_target_list_with_an_unrecognized_page_is_not_cached(monkeypatch, sch):
    # An empty sky is a real answer; a page we cannot read is a change to report.
    counter = _Counter()

    def fake_post(url, data=None, headers=None, timeout=None):
        counter.calls += 1
        return FakeRequestsSuccessResponse(b"<html><body>nope</body></html>")

    monkeypatch.setattr(sch.requests, "post", fake_post)
    assert sch.observing_target_list_scraper("https://mpc", {"latitude": "45.0"}) == []
    assert sch.observing_target_list_scraper("https://mpc", {"latitude": "45.0"}) == []
    assert counter.count == 2, "an unreadable page must not be stored as the answer"


def test_an_empty_sky_is_cached(monkeypatch, sch):
    counter = _Counter()
    empty_table = (
        b"<html><body><table><tr><th>Designation</th><th>Mag</th><th>Time</th>"
        b"<th>RA</th><th>Dec</th><th>Alt</th></tr></table></body></html>"
    )

    def fake_post(url, data=None, headers=None, timeout=None):
        counter.calls += 1
        return FakeRequestsSuccessResponse(empty_table)

    monkeypatch.setattr(sch.requests, "post", fake_post)
    assert sch.observing_target_list_scraper("https://mpc", {"latitude": "45.0"}) == []
    assert sch.observing_target_list_scraper("https://mpc", {"latitude": "45.0"}) == []
    assert counter.count == 1, "an empty result is still a real answer"


def test_second_neocp_fetch_is_served_from_the_cache(monkeypatch, fresh_config, sch):
    sample = [
        {
            "Temp_Desig": "P10abcd",
            "Score": "100",
            "R.A.": "10.0",
            "Decl": "20.0",
            "V": "18.0",
            "NObs": "5",
            "Arc": "0.1",
            "Not_Seen_dys": "1",
        }
    ]
    counter = _Counter()

    async def fake_httpx_get(url, payload, return_type):
        counter.calls += 1
        return sample, 200

    async def fake_get_neocp_ephemeris(config, object_names):
        return {}

    monkeypatch.setattr(sch, "httpx_get", fake_httpx_get)
    monkeypatch.setattr(sch, "get_neocp_ephemeris", fake_get_neocp_ephemeris)

    first = asyncio.run(sch.fetch_neocp_json_and_ephemeris(fresh_config))
    second = asyncio.run(sch.fetch_neocp_json_and_ephemeris(fresh_config))

    assert first[0] == second[0] == sample
    assert first[2] is True
    assert counter.count == 1, "neocp.json is a live feed but still worth caching"


def test_neocp_falls_back_to_the_cached_feed_when_the_network_dies(
    monkeypatch, fresh_config, sch
):
    sample = [{"Temp_Desig": "P10abcd", "Score": "100"}]
    counter = _Counter()

    async def fake_httpx_get(url, payload, return_type):
        counter.calls += 1
        return sample, 200

    async def fake_get_neocp_ephemeris(config, object_names):
        return {}

    monkeypatch.setattr(sch, "httpx_get", fake_httpx_get)
    monkeypatch.setattr(sch, "get_neocp_ephemeris", fake_get_neocp_ephemeris)
    asyncio.run(sch.fetch_neocp_json_and_ephemeris(fresh_config))

    async def unreachable(url, payload, return_type):
        return {}, 0

    monkeypatch.setattr(sch, "httpx_get", unreachable)
    cached = asyncio.run(sch.fetch_neocp_json_and_ephemeris(fresh_config))

    assert cached[0] == sample, "a live feed from disk beats an empty table"
    assert cached[2] is True


def test_neocp_without_a_cache_still_reports_the_failure(
    monkeypatch, fresh_config, sch
):
    async def unreachable(url, payload, return_type):
        return {}, 0

    async def fake_get_neocp_ephemeris(config, object_names):
        return {}

    monkeypatch.setattr(sch, "httpx_get", unreachable)
    monkeypatch.setattr(sch, "get_neocp_ephemeris", fake_get_neocp_ephemeris)

    data, response, ok = asyncio.run(sch.fetch_neocp_json_and_ephemeris(fresh_config))
    assert (data, response, ok) == ([], {}, False)


def test_second_neocp_ephemeris_call_is_served_from_the_cache(
    monkeypatch, fresh_config, sch
):
    counter = _Counter()
    html = (
        "<html><body><b>P10abcd</b><pre>header\nintermediate\n"
        "a b c d e f g h i j k l 1.5 45.0</pre></body></html>"
    )

    class Response:
        text = html
        status_code = 200

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, *args, **kwargs):
            counter.calls += 1
            return Response()

    monkeypatch.setattr(sch.httpx, "AsyncClient", lambda *a, **k: Client())

    first = asyncio.run(sch.get_neocp_ephemeris(fresh_config, ["P10abcd"]))
    second = asyncio.run(sch.get_neocp_ephemeris(fresh_config, ["P10abcd"]))

    assert first == second
    assert "P10abcd" in first
    assert counter.count == 1, "the confirmeph2 POST must not be repeated"


def test_neocp_ephemeris_cache_key_follows_the_viewing_point(
    monkeypatch, fresh_config, sch
):
    # Moving the observatory must invalidate ephemerides computed for the old
    # site, or the velocity and direction would belong to another position.
    counter = _Counter()
    html = (
        "<html><body><b>P10abcd</b><pre>header\nintermediate\n"
        "a b c d e f g h i j k l 1.5 45.0</pre></body></html>"
    )

    class Response:
        text = html
        status_code = 200

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, *args, **kwargs):
            counter.calls += 1
            return Response()

    monkeypatch.setattr(sch.httpx, "AsyncClient", lambda *a, **k: Client())

    asyncio.run(sch.get_neocp_ephemeris(fresh_config, ["P10abcd"]))
    fresh_config["Observatory"]["latitude"] = "46.0"
    asyncio.run(sch.get_neocp_ephemeris(fresh_config, ["P10abcd"]))

    assert counter.count == 2


def test_object_ephemeris_is_left_to_the_astroquery_cache(
    monkeypatch, fresh_config, sch
):
    # A1: the MPC ephemeris lookup keeps astroquery's own cache, which already
    # stores it for a week. Double-caching it here would only duplicate that.
    def forbidden(*args, **kwargs):
        raise AssertionError("object_ephemeris must not use the project cache")

    monkeypatch.setattr(sch.cache, "fetch_cached", forbidden)
    monkeypatch.setattr(sch.cache, "fetch_cached_async", forbidden)
    monkeypatch.setattr(
        sch.MPC,
        "get_ephemeris",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(sch.configuration, "load_config", lambda conf: None)

    # It fails later, on the None table, which is not the point: the point is
    # that reaching the cache at all is the failure.
    with pytest.raises((AttributeError, TypeError, IndexError, KeyError)):
        sch.object_ephemeris(fresh_config, "CERES", "h")


def test_cache_can_be_disabled_end_to_end(monkeypatch, fresh_config, sch):
    payload = {"init": "2026092500", "dataseries": []}
    counter = _Counter()
    monkeypatch.setattr(sch.requests, "get", _counting_get(payload, counter))
    monkeypatch.setenv(sch.cache.NO_CACHE_ENV_VAR, "1")

    sch.weather_forecast_raw(fresh_config)
    sch.weather_forecast_raw(fresh_config)

    assert counter.count == 2, "a disabled cache must always ask the network"
