import gettext
from configparser import ConfigParser
from importlib.resources import files
from pathlib import Path

import asteroidpy.configuration as configuration


def get_locale_dir() -> Path:
    """Return the packaged ``asteroidpy/locales`` directory."""

    return Path(files("asteroidpy").joinpath("locales"))


def setup_gettext(config: ConfigParser) -> None:
    """Install gettext translator for ``builtins._`` using ``locales/<lang>/LC_MESSAGES/base.mo``.

    Reads ``General.lang``, builds ``gettext.translation(..., fallback=True)`` so missing
    catalogue strings fall back to the original English ``msgid`` text, then
    ``translator.install()`` so user code picks up gettext via ``builtins._``.
    """

    configuration.load_config(config)
    lang = config.get("General", "lang", fallback="en")
    locale_dir = str(get_locale_dir())
    translator = gettext.translation(
        "base",
        localedir=locale_dir,
        languages=[lang],
        fallback=True,
    )
    translator.install()
