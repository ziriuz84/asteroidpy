"""Text helper: resolves ``builtins._`` installed by gettext (if any)."""

import builtins


def translate(message: str) -> str:
    trans = getattr(builtins, "_", None)
    if callable(trans):
        return str(trans(message))
    return message
