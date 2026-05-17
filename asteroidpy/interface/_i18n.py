import gettext
import os
from configparser import ConfigParser

import asteroidpy.configuration as configuration


def setup_gettext(config: ConfigParser) -> None:
    """Install gettext translator for ``builtins._`` from ``locales/``."""

    configuration.load_config(config)
    lang = config.get("General", "lang", fallback="en")
    locale_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "locales")
    )
    translator = gettext.translation(
        "base",
        localedir=locale_dir,
        languages=[lang],
        fallback=True,
    )
    translator.install()
