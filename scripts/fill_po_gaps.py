#!/usr/bin/env python3
"""Fill known untranslated msgids in AsteroidPy locale catalogs (run after xgettext/msgmerge).

Usage:
  python scripts/fill_po_gaps.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import polib

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCALES = REPO_ROOT / "locales"

# msgid → per-locale msgstr (en uses msgid as msgstr via None sentinel)
GAP_STRINGS: dict[str, dict[str, str]] = {
    "Update coordinates? (y/N) -> ": {
        "en": "",
        "it": "Aggiornare le coordinate? (s/N) -> ",
        "de": "Koordinaten aktualisieren? (j/N) -> ",
        "es": "¿Actualizar las coordenadas? (s/N) -> ",
        "fr": "Mettre à jour les coordonnées ? (o/N) -> ",
        "pt": "Atualizar as coordenadas? (s/N) -> ",
    },
    (
        "Could not fetch observatory coordinates from the MPC "
        "(check the code and your network connection)."
    ): {
        "en": "",
        "it": (
            "Impossibile recuperare le coordinate dell'osservatorio dall'MPC "
            "(verifica il codice e la connessione di rete)."
        ),
        "de": (
            "Observatoriumskoordinaten konnten nicht vom MPC abgerufen werden "
            "(Code und Netzwerkverbindung prüfen)."
        ),
        "es": (
            "No se pudieron obtener las coordenadas del observatorio desde el MPC "
            "(comprueba el código y la conexión de red)."
        ),
        "fr": (
            "Impossible de récupérer les coordonnées de l'observatoire depuis le MPC "
            "(vérifiez le code et la connexion réseau)."
        ),
        "pt": (
            "Não foi possível obter as coordenadas do observatório a partir do MPC "
            "(verifique o código e a ligação de rede)."
        ),
    },
    "End of input (EOF); exiting.": {
        "en": "",
        "it": "Fine input (EOF); uscita.",
        "de": "Ende der Eingabe (EOF); Programm wird beendet.",
        "es": "Fin de entrada (EOF); saliendo.",
        "fr": "Fin de saisie (EOF) ; arrêt.",
        "pt": "Fim da entrada (EOF); a terminar.",
    },
    "You must enter an integer.": {
        "en": "",
        "it": "Devi inserire un numero intero.",
        "de": "Sie müssen eine ganze Zahl eingeben.",
        "es": "Debe introducir un número entero.",
        "fr": "Vous devez saisir un nombre entier.",
        "pt": "Tem de introduzir um número inteiro.",
    },
    "You must enter a number.": {
        "en": "",
        "it": "Devi inserire un numero.",
        "de": "Sie müssen eine Zahl eingeben.",
        "es": "Debe introducir un número.",
        "fr": "Vous devez saisir un nombre.",
        "pt": "Tem de introduzir um número.",
    },
    "Enter an integer between {low} and {high}.": {
        "en": "",
        "it": "Inserisci un intero tra {low} e {high}.",
        "de": "Geben Sie eine ganze Zahl zwischen {low} und {high} ein.",
        "es": "Introduzca un entero entre {low} y {high}.",
        "fr": "Saisissez un entier entre {low} et {high}.",
        "pt": "Introduza um inteiro entre {low} e {high}.",
    },
    (
        "Could not load a fresh MPC form token from the What's Observable page; "
        "using an embedded fallback. The request might fail."
    ): {
        "en": "",
        "it": (
            "Impossibile caricare un token di modulo MPC aggiornato dalla pagina "
            "What's Observable; si usa un fallback incorporato. La richiesta potrebbe fallire."
        ),
        "de": (
            "Frisches MPC-Formular-Token konnte nicht von der "
            "„What's Observable“-Seite geladen werden; es wird ein eingebetteter "
            "Ersatzwert verwendet. Die Anfrage könnte fehlschlagen."
        ),
        "es": (
            "No se pudo cargar un token de formulario MPC reciente desde "
            "la página What's Observable; se usa uno integrado de respaldo. "
            "La solicitud podría fallar."
        ),
        "fr": (
            "Impossible de charger un jeton de formulaire MPC récent depuis "
            "la page What's Observable ; utilisation d'une valeur intégrée de "
            "secours. La requête peut échouer."
        ),
        "pt": (
            "Não foi possível carregar um token de formulário MPC recente "
            "a partir da página What's Observable; a usar uma alternativa "
            "incorporada. O pedido pode falhar."
        ),
    },
    "Civil twilight: {m} – {e}": {
        "en": "",
        "it": "Crepuscolo civile: {m} – {e}",
        "de": "Bürgerliche Dämmerung: {m} – {e}",
        "es": "Crepúsculo civil: {m} – {e}",
        "fr": "Crépuscule civil : {m} – {e}",
        "pt": "Crepúsculo civil: {m} – {e}",
    },
    "Nautical twilight: {m} – {e}": {
        "en": "",
        "it": "Crepuscolo nautico: {m} – {e}",
        "de": "Nautische Dämmerung: {m} – {e}",
        "es": "Crepúsculo náutico: {m} – {e}",
        "fr": "Crépuscule nautique : {m} – {e}",
        "pt": "Crepúsculo náutico: {m} – {e}",
    },
    "Astronomical twilight: {m} – {e}": {
        "en": "",
        "it": "Crepuscolo astronomico: {m} – {e}",
        "de": "Astronomische Dämmerung: {m} – {e}",
        "es": "Crepúsculo astronómico: {m} – {e}",
        "fr": "Crépuscule astronomique : {m} – {e}",
        "pt": "Crepúsculo astronómico: {m} – {e}",
    },
    "Sunrise: {t}": {
        "en": "",
        "it": "Alba: {t}",
        "de": "Sonnenaufgang: {t}",
        "es": "Amanecer: {t}",
        "fr": "Lever du Soleil : {t}",
        "pt": "Nascer do sol: {t}",
    },
    "Sunset: {t}": {
        "en": "",
        "it": "Tramonto: {t}",
        "de": "Sonnenuntergang: {t}",
        "es": "Atardecer: {t}",
        "fr": "Coucher du Soleil : {t}",
        "pt": "Pôr do sol: {t}",
    },
    "Moonrise: {t}": {
        "en": "",
        "it": "Levata lunare: {t}",
        "de": "Mondaufgang: {t}",
        "es": "Salida de la Luna: {t}",
        "fr": "Lever de la Lune : {t}",
        "pt": "Nascer da Lua: {t}",
    },
    "Moonset: {t}": {
        "en": "",
        "it": "Tramonto lunare: {t}",
        "de": "Monduntergang: {t}",
        "es": "Puesta de la Luna: {t}",
        "fr": "Coucher de la Lune : {t}",
        "pt": "Pôr da Lua: {t}",
    },
    "Moon illumination: {f}": {
        "en": "",
        "it": "Illuminazione lunare: {f}",
        "de": "Mondbeleuchtung: {f}",
        "es": "Iluminación lunar: {f}",
        "fr": "Illumination de la Lune : {f}",
        "pt": "Iluminação da Lua: {f}",
    },
    "Invalid choice — enter m, h, d, or w.": {
        "en": "",
        "it": "Scelta non valida — inserisci m, h, d o w.",
        "de": "Ungültige Eingabe — geben Sie m, h, d oder w ein.",
        "es": "Selección no válida — introduce m, h, d o w.",
        "fr": "Choix invalide — saisissez m, h, d ou w.",
        "pt": "Escolha inválida — introduza m, h, d ou w.",
    },
}


def main() -> None:
    locale_dirs = sorted(p for p in LOCALES.iterdir() if p.is_dir() and not p.name.startswith("."))
    for loc in locale_dirs:
        code = loc.name
        po_path = loc / "LC_MESSAGES" / "base.po"
        if not po_path.is_file():
            continue

        po = polib.pofile(str(po_path))
        changed = 0
        for entry in po:
            if entry.obsolete or not entry.msgid:
                continue
            if entry.msgid not in GAP_STRINGS:
                continue
            per_lang = GAP_STRINGS[entry.msgid]
            target = per_lang.get(code, "")
            if code == "en":
                target = entry.msgid
            if not target:
                continue
            entry.msgstr = target
            if entry.fuzzy:
                entry.previous_msgid = None
                entry.previous_msgid_plural = None
                entry.previous_msgctxt = None
                flags = []
                entry.flags = [f for f in entry.flags if f != "fuzzy"]
            changed += 1

        if changed:
            po.save(po_path.as_posix())

        subprocess.run(
            ["msgfmt", "-o", (loc / "LC_MESSAGES" / "base.mo").as_posix(), po_path.as_posix()],
            check=True,
            cwd=str(REPO_ROOT),
        )


if __name__ == "__main__":
    main()
