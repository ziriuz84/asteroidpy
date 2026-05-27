"""Verify packaged locale catalogs ship with the installed package."""

from importlib.resources import files


def test_packaged_locale_mo_files_exist() -> None:
    locale_root = files("asteroidpy") / "locales"
    for lang in ("en", "it", "de", "fr", "es", "pt"):
        mo = locale_root / lang / "LC_MESSAGES" / "base.mo"
        assert mo.is_file(), f"missing packaged catalog: {mo}"


def test_get_locale_dir_resolves_to_existing_directory() -> None:
    from asteroidpy.interface._i18n import get_locale_dir

    locale_dir = get_locale_dir()
    assert locale_dir.is_dir()
    assert (locale_dir / "en" / "LC_MESSAGES" / "base.mo").is_file()
