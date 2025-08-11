import asyncio
import io
from configparser import ConfigParser
from typing import Any, Dict, List

import pytest


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


def test_httpx_get_and_post(monkeypatch, sch):
    class DummyResponse:
        def __init__(self, payload: Dict[str, Any]):
            self._payload = payload
            self.text = "<ok/>"
            self.status_code = 200

        def json(self) -> Dict[str, Any]:
            return self._payload

    class DummyAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, params=None):
            return DummyResponse({"url": url, "params": params})

        async def post(self, url, data=None):
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


def test_is_visible_quadrants(fresh_config, monkeypatch, sch):
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
    assert sch.is_visible(fresh_config, FakeCoord(90.0, 30.0), sch.Time.now()) is True
    # South (135-225)
    assert sch.is_visible(fresh_config, FakeCoord(180.0, 30.0), sch.Time.now()) is True
    # West (225-315)
    assert sch.is_visible(fresh_config, FakeCoord(270.0, 30.0), sch.Time.now()) is True
    # North sector check as implemented (315..45) is impossible; expect False
    assert sch.is_visible(fresh_config, FakeCoord(0.0, 30.0), sch.Time.now()) is False


def test_observing_target_list_scraper_parses_table(monkeypatch, sch):
    # Construct HTML with at least 4 tables, the fourth containing headers and a row
    html = (
        "<html><body>"
        "<table></table>"  # 0
        "<table></table>"  # 1
        "<table></table>"  # 2
        "<table>"  # 3
        "  <tr><th>Designation</th><th>Mag</th><th>t2</th><th>t3</th><th>Time</th><th>RA</th><th>Dec</th><th>Alt</th></tr>"
        "  <tr><td>2025 AB</td><td>18.2</td><td>x</td><td>y</td><td>2025-01-01T00:00z</td><td>12 00 00</td><td>-30 00 00</td><td>45</td></tr>"
        "</table>"
        "</body></html>"
    ).encode("utf-8")

    class DummyResp:
        def __init__(self, content: bytes):
            self.content = content

    monkeypatch.setattr(sch.requests, "post", lambda url, params=None: DummyResp(html))

    data = sch.observing_target_list_scraper("https://mpc", {"k": "v"})

    # Expect at least one non-empty row present
    assert any(row for row in data), "Expected at least one parsed row"
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
    rows: List[List[str]] = [
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


def test_neocp_confirmation_returns_table_even_when_filtering_all(monkeypatch, fresh_config, sch):
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

    async def fake_httpx_get(url: str, payload: Dict[str, Any], return_type: str):
        return [sample, 200]

    monkeypatch.setattr(sch, "httpx_get", fake_httpx_get)
    monkeypatch.setattr(sch, "is_visible", lambda c, coord, t: True)

    tbl = sch.neocp_confirmation(fresh_config, min_score=100, max_magnitude=20, min_altitude=20)
    # Should return a QTable with the right columns and zero rows
    assert list(tbl.colnames) == [
        "Temp_Desig",
        "Score",
        "R.A.",
        "Decl",
        "Alt",
        "V",
        "NObs",
        "Arc",
        "Not_seen",
    ]
    assert len(tbl) == 0


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
    calls: Dict[str, Any] = {}

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
