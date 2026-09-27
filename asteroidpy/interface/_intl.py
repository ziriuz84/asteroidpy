"""Text helper: resolves ``builtins._`` installed by gettext (if any)."""

import builtins

from asteroidpy.configuration import OBSERVATORY_FIELD_LABELS


def translate(message: str) -> str:
    trans = getattr(builtins, "_", None)
    if callable(trans):
        return str(trans(message))
    return message


def observatory_labels() -> dict[str, str]:
    """Return the ``[Observatory]`` labels localized for the active gettext locale.

    :mod:`asteroidpy.configuration` is gettext-free on purpose, so both frontends —
    the Textual screens and the legacy text menus — resolve the msgids in
    :data:`~asteroidpy.configuration.OBSERVATORY_FIELD_LABELS` here and pass the
    result as ``labels``. Call it again after a language change: the mapping follows
    whichever catalog is installed.
    """

    return {
        option: translate(label)
        for option, label, _sensitive in OBSERVATORY_FIELD_LABELS
    }
