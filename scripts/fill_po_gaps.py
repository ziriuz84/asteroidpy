#!/usr/bin/env python3
"""Fill known untranslated msgids in AsteroidPy locale catalogs (run after xgettext/msgmerge).

Usage:
  python scripts/fill_po_gaps.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import polib

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCALES = REPO_ROOT / "locales"

# msgid → per-locale msgstr (empty "en" means use msgid unless "en" override is set)
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
    "Invalid date or time (check day/month ranges and hour 0–23); please try again.": {
        "en": "",
        "it": "Data o ora non valida (controlla giorno/mese e ora 0–23); riprova.",
        "de": (
            "Ungültiges Datum oder ungültige Uhrzeit "
            "(Tag/Monat und Stunde 0–23 prüfen); bitte erneut versuchen."
        ),
        "es": "Fecha u hora no válida (comprueba día/mes y hora 0–23); inténtelo de nuevo.",
        "fr": (
            "Date ou heure non valide (vérifiez jour/mois et heure 0–23) ; "
            "veuillez réessayer."
        ),
        "pt": "Data ou hora inválida (verifique dia/mês e hora 0–23); tente novamente.",
    },
    "Nord Altitude -> ": {
        "en": "North Altitude -> ",
        "it": "Altitudine Nord -> ",
        "de": "Nordhöhe -> ",
        "es": "Altitud norte -> ",
        "fr": "Altitude nord -> ",
        "pt": "Altitude norte -> ",
    },
    "0 - Back": {
        "en": "",
        "it": "0 - Indietro",
        "de": "0 - Zurück",
        "es": "0 - Atrás",
        "fr": "0 - Retour",
        "pt": "0 - Voltar",
    },
    "Language updated.": {
        "en": "",
        "it": "Lingua aggiornata.",
        "de": "Sprache wurde aktualisiert.",
        "es": "Idioma actualizado.",
        "fr": "Langue mise à jour.",
        "pt": "Idioma atualizado.",
    },
    "(No observatory section)": {
        "en": "",
        "it": "(Nessuna sezione osservatorio)",
        "de": "(Keine Observatoriumsdaten)",
        "es": "(Sin sección de observatorio)",
        "fr": "(Aucune section observatoire)",
        "pt": "(Sem secção de observatório)",
    },
    "1 - Change coordinates": {
        "en": "",
        "it": "1 - Modifica coordinate",
        "de": "1 - Koordinaten ändern",
        "es": "1 - Cambiar coordenadas",
        "fr": "1 - Modifier les coordonnées",
        "pt": "1 - Alterar coordenadas",
    },
    "2 - Change altitude": {
        "en": "",
        "it": "2 - Modifica altitudine",
        "de": "2 - Höhe ändern",
        "es": "2 - Cambiar altitud",
        "fr": "2 - Modifier l'altitude",
        "pt": "2 - Alterar altitude",
    },
    "3 - Change the name of the observer": {
        "en": "",
        "it": "3 - Modifica il nome dell'osservatore",
        "de": "3 - Namen des Beobachters ändern",
        "es": "3 - Cambiar el nombre del observador",
        "fr": "3 - Modifier le nom de l'observateur",
        "pt": "3 - Alterar nome do observador",
    },
    "4 - Change the name of the observatory": {
        "en": "",
        "it": "4 - Modifica il nome dell'osservatorio",
        "de": "4 - Namen des Observatoriums ändern",
        "es": "4 - Cambiar el nombre del observatorio",
        "fr": "4 - Modifier le nom de l'observatoire",
        "pt": "4 - Alterar nome do observatório",
    },
    "5 - Change the MPC code": {
        "en": "",
        "it": "5 - Modifica il codice MPC",
        "de": "5 - MPC-Code ändern",
        "es": "5 - Cambiar el código MPC",
        "fr": "5 - Modifier le code MPC",
        "pt": "5 - Alterar o código MPC",
    },
    "6 - Change Virtual Horizon": {
        "en": "",
        "it": "6 - Modifica orizzonte virtuale",
        "de": "6 - Virtuellen Horizont ändern",
        "es": "6 - Cambiar horizonte virtual",
        "fr": "6 - Modifier l'horizon virtuel",
        "pt": "6 - Alterar horizonte virtual",
    },
    "Change coordinates": {
        "en": "",
        "it": "Modifica coordinate",
        "de": "Koordinaten ändern",
        "es": "Cambiar coordenadas",
        "fr": "Modifier les coordonnées",
        "pt": "Alterar coordenadas",
    },
    "Save": {
        "en": "",
        "it": "Salva",
        "de": "Speichern",
        "es": "Guardar",
        "fr": "Enregistrer",
        "pt": "Guardar",
    },
    "Cancel": {
        "en": "",
        "it": "Annulla",
        "de": "Abbrechen",
        "es": "Cancelar",
        "fr": "Annuler",
        "pt": "Cancelar",
    },
    "Change altitude": {
        "en": "",
        "it": "Modifica altitudine",
        "de": "Höhe ändern",
        "es": "Cambiar altitud",
        "fr": "Modifier l'altitude",
        "pt": "Alterar altitude",
    },
    "Change observer": {
        "en": "",
        "it": "Modifica osservatore",
        "de": "Beobachter ändern",
        "es": "Cambiar observador",
        "fr": "Modifier l'observateur",
        "pt": "Alterar observador",
    },
    "Change observatory name": {
        "en": "",
        "it": "Modifica nome osservatorio",
        "de": "Observatoriumsnamen ändern",
        "es": "Cambiar nombre del observatorio",
        "fr": "Modifier le nom de l'observatoire",
        "pt": "Alterar nome do observatório",
    },
    "Change MPC code": {
        "en": "",
        "it": "Modifica codice MPC",
        "de": "MPC-Code ändern",
        "es": "Cambiar código MPC",
        "fr": "Modifier le code MPC",
        "pt": "Alterar código MPC",
    },
    "Update coordinates?": {
        "en": "",
        "it": "Aggiornare le coordinate?",
        "de": "Koordinaten aktualisieren?",
        "es": "¿Actualizar las coordenadas?",
        "fr": "Mettre à jour les coordonnées ?",
        "pt": "Atualizar as coordenadas?",
    },
    "Virtual horizon": {
        "en": "",
        "it": "Orizzonte virtuale",
        "de": "Virtueller Horizont",
        "es": "Horizonte virtual",
        "fr": "Horizon virtuel",
        "pt": "Horizonte virtual",
    },
    "1 - Weather forecast": {
        "en": "",
        "it": "1 - Previsioni meteo",
        "de": "1 - Wettervorhersage",
        "es": "1 - Previsión meteorológica",
        "fr": "1 - Prévisions météo",
        "pt": "1 - Previsão meteorológica",
    },
    "2 - Observing target List": {
        "en": "",
        "it": "2 - Lista target di osservazione",
        "de": "2 - Beobachtungsliste",
        "es": "2 - Lista de objetivos de observación",
        "fr": "2 - Liste des cibles d'observation",
        "pt": "2 - Lista de alvos de observação",
    },
    "3 - NEOcp list": {
        "en": "",
        "it": "3 - Lista NEOcp",
        "de": "3 - NEOcp-Liste",
        "es": "3 - Lista NEOcp",
        "fr": "3 - Liste NEOcp",
        "pt": "3 - Lista NEOcp",
    },
    "4 - Object Ephemeris": {
        "en": "",
        "it": "4 - Effemeridi oggetto",
        "de": "4 - Objektephemeriden",
        "es": "4 - Efemérides del objeto",
        "fr": "4 - Éphémérides de l'objet",
        "pt": "4 - Efemérides do objeto",
    },
    "5 - Twilight Times": {
        "en": "",
        "it": "5 - Orari crepuscolo",
        "de": "5 - Dämmerungszeiten",
        "es": "5 - Horarios del crepúsculo",
        "fr": "5 - Heures du crépuscule",
        "pt": "5 - Horários do crepúsculo",
    },
    "Weather forecast": {
        "en": "",
        "it": "Previsioni meteo",
        "de": "Wettervorhersage",
        "es": "Previsión meteorológica",
        "fr": "Prévisions météo",
        "pt": "Previsão meteorológica",
    },
    "Fetch forecast": {
        "en": "",
        "it": "Scarica previsione",
        "de": "Vorhersage abrufen",
        "es": "Obtener previsión",
        "fr": "Obtenir les prévisions",
        "pt": "Obter previsão",
    },
    "Observing target list": {
        "en": "",
        "it": "Lista target di osservazione",
        "de": "Beobachtungsliste",
        "es": "Lista de objetivos de observación",
        "fr": "Liste des cibles d'observation",
        "pt": "Lista de alvos de observação",
    },
    "Use observation time \"now\" (UTC)": {
        "en": "",
        "it": 'Usa orario di osservazione "adesso" (UTC)',
        "de": "Beobachtungszeit „jetzt“ (UTC) verwenden",
        "es": "Usar hora de observación «ahora» (UTC)",
        "fr": "Utiliser l'heure d'observation « maintenant » (UTC)",
        "pt": "Usar hora de observação «agora» (UTC)",
    },
    "Start time (UTC) if not \"now\"": {
        "en": "",
        "it": 'Orario di inizio (UTC) se non "adesso"',
        "de": "Startzeit (UTC), wenn nicht „jetzt“",
        "es": "Hora de inicio (UTC) si no es «ahora»",
        "fr": "Heure de début (UTC) si ce n'est pas « maintenant »",
        "pt": "Hora de início (UTC) se não for «agora»",
    },
    "Day": {
        "en": "",
        "it": "Giorno",
        "de": "Tag",
        "es": "Día",
        "fr": "Jour",
        "pt": "Dia",
    },
    "Month": {
        "en": "",
        "it": "Mese",
        "de": "Monat",
        "es": "Mes",
        "fr": "Mois",
        "pt": "Mês",
    },
    "Year": {
        "en": "",
        "it": "Anno",
        "de": "Jahr",
        "es": "Año",
        "fr": "Année",
        "pt": "Ano",
    },
    "Hour": {
        "en": "",
        "it": "Ora",
        "de": "Stunde",
        "es": "Hora",
        "fr": "Heure",
        "pt": "Hora",
    },
    "Minutes": {
        "en": "",
        "it": "Minuti",
        "de": "Minuten",
        "es": "Minutos",
        "fr": "Minutes",
        "pt": "Minutos",
    },
    "Seconds": {
        "en": "",
        "it": "Secondi",
        "de": "Sekunden",
        "es": "Segundos",
        "fr": "Secondes",
        "pt": "Segundos",
    },
    "Asteroids": {
        "en": "",
        "it": "Asteroidi",
        "de": "Asteroiden",
        "es": "Asteroides",
        "fr": "Astéroïdes",
        "pt": "Asteroides",
    },
    "NEAs": {
        "en": "",
        "it": "NEAs",
        "de": "NEAs",
        "es": "NEAs",
        "fr": "NEAs",
        "pt": "NEAs",
    },
    "Comets": {
        "en": "",
        "it": "Comete",
        "de": "Kometen",
        "es": "Cometas",
        "fr": "Comètes",
        "pt": "Cometas",
    },
    "Open result in browser": {
        "en": "",
        "it": "Apri il risultato nel browser",
        "de": "Ergebnis im Browser öffnen",
        "es": "Abrir el resultado en el navegador",
        "fr": "Ouvrir le résultat dans le navigateur",
        "pt": "Abrir o resultado no navegador",
    },
    "Run": {
        "en": "",
        "it": "Esegui",
        "de": "Ausführen",
        "es": "Ejecutar",
        "fr": "Exécuter",
        "pt": "Executar",
    },
    "Done. Table opened in browser.": {
        "en": "",
        "it": "Fatto. Tabella aperta nel browser.",
        "de": "Fertig. Tabelle im Browser geöffnet.",
        "es": "Hecho. Tabla abierta en el navegador.",
        "fr": "Terminé. Tableau ouvert dans le navigateur.",
        "pt": "Concluído. Tabela aberta no navegador.",
    },
    "Close": {
        "en": "",
        "it": "Chiudi",
        "de": "Schließen",
        "es": "Cerrar",
        "fr": "Fermer",
        "pt": "Fechar",
    },
    "NEOcp confirmation": {
        "en": "",
        "it": "Conferma NEOcp",
        "de": "NEOcp-Bestätigung",
        "es": "Confirmación NEOcp",
        "fr": "Confirmation NEOcp",
        "pt": "Confirmação NEOcp",
    },
    "You must enter valid numeric fields.": {
        "en": "",
        "it": "Inserisci valori numerici validi nei campi.",
        "de": "Bitte gültige Zahlen in allen Feldern eingeben.",
        "es": "Debe introducir valores numéricos válidos en los campos.",
        "fr": "Saisissez des valeurs numériques valides dans les champs.",
        "pt": "Introduza valores numéricos válidos nos campos.",
    },
    "Object ephemeris": {
        "en": "",
        "it": "Effemeridi dell'oggetto",
        "de": "Objektephemeriden",
        "es": "Efemérides del objeto",
        "fr": "Éphémérides de l'objet",
        "pt": "Efemérides do objeto",
    },
    "Twilight & Sun/Moon": {
        "en": "",
        "it": "Crepuscolo e Sole/Luna",
        "de": "Dämmerung und Sonne/Mond",
        "es": "Crepúsculo y Sol/Luna",
        "fr": "Crépuscule et Soleil/Lune",
        "pt": "Crepúsculo e Sol/Lua",
    },
    "Compute": {
        "en": "",
        "it": "Calcola",
        "de": "Berechnen",
        "es": "Calcular",
        "fr": "Calculer",
        "pt": "Calcular",
    },
}


def _resolve_target(per_lang: dict[str, str], code: str, msgid: str) -> str | None:
    if code == "en":
        override = per_lang.get("en", "")
        if override:
            return override
        return msgid
    return per_lang.get(code, "")


def main() -> None:
    locale_dirs = sorted(p for p in LOCALES.iterdir() if p.is_dir() and not p.name.startswith("."))
    msgfmt_missing_warned = False
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
            target = _resolve_target(per_lang, code, entry.msgid)
            if not target:
                continue
            entry.msgstr = target
            if entry.fuzzy:
                entry.previous_msgid = None
                entry.previous_msgid_plural = None
                entry.previous_msgctxt = None
                entry.flags = [f for f in entry.flags if f != "fuzzy"]
            changed += 1

        if changed:
            po.save(po_path.as_posix())

        msgfmt = shutil.which("msgfmt")
        if not msgfmt:
            if not msgfmt_missing_warned:
                print(
                    "msgfmt not found in PATH; install gettext to compile .mo files "
                    "(.po files were still updated).",
                    file=sys.stderr,
                )
                msgfmt_missing_warned = True
            continue
        mo_path = loc / "LC_MESSAGES" / "base.mo"
        try:
            subprocess.run(
                [msgfmt, "-o", mo_path.as_posix(), po_path.as_posix()],
                check=True,
                cwd=str(REPO_ROOT),
            )
        except subprocess.CalledProcessError as exc:
            print(
                f"msgfmt failed for {po_path} (exit {exc.returncode}).",
                file=sys.stderr,
            )


if __name__ == "__main__":
    main()
