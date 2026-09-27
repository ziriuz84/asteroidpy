# PROMPTS

Prompt di esecuzione, uno per task della roadmap. Ogni sezione è autonoma: si
può dare in pasto a un agente senza leggere il resto del file.

Prima di iniziare, leggere `AGENTS.md` (gate di lint, regole doc, vincoli CI) e
`CONTRIBUTING.md` (architettura, traduzioni). I vincoli elencati in
[Vincoli comuni](#vincoli-comuni) valgono per tutti i task e non vanno ripetuti
nei prompt.

Ordine di esecuzione suggerito:

```
F1 → F9 → F7 → F2 → F6 → A1 → A2 → A3 → B1 → D1 → C1 → C2 → C3 → E1 → F3 → F4 → F5 → F8
```

Bug e cleanup prima delle feature, così il resto poggia su una base pulita.
`A3` dipende da `A1` (l'offline usa la cache). `F8` va LASTO perché tocca tutti
i client di rete introdotti dai task precedenti.

---

## Vincoli comuni

Valgono per ogni task di questo file.

- **Gate di lint (identico allo stage `Lint` della Jenkinsfile)**:
  `ruff check asteroidpy/ tests/`, `mypy asteroidpy/`, `isort --check asteroidpy/ tests/`,
  `black --check asteroidpy/ tests/`. Tutti verdi prima di dichiarare finito.
- **Test**: `pytest -q` verde. Aggiungere test per ogni comportamento nuovo
  (preferire test parametrizzati, piccoli e isolati).
- **Documentazione**: `README.md` e `docs/source/*.rst` devono restare coerenti
  fra loro e con il codice. Ogni nuova funzione pubblica ha una docstring; ogni
  modulo autodoc'd ha una docstring di modulo. In `docs/source/asteroidpy.rst`
  preferire un riferimento `:func:` reale a una prosa.
- **Non modificare `CHANGELOG.md`**: è generato da `./release.sh` / `./ghrelease.sh`.
- **Non creare `.github/workflows/`**: la CI è Jenkins (`Jenkinsfile`).
- **Non modificare `PROMPTS.md`** se non è il task che lo richiede.
- **Nessun segreto nel sorgente**: niente token, chiavi o URL con credenziali.
- **Non allargare `lint.select`** in `pyproject.toml` senza sistemare tutto il codebase.
- **Lingua**: docstring e commenti in inglese, come nel resto del codice.

---

## F1 — Correggere il riepilogo osservatorio e tradurre le etichette

**Contesto** — `asteroidpy/interface/_tui_screens.py:81` (`_observatory_summary`),
`asteroidpy/configuration.py:277` (`print_obs_config`).

**Problema** — `_observatory_summary` chiama `print_obs_config(config)` senza
`show_sensitive=True`, quindi la schermata Osservatorio mostra sempre
`latitude/longitude/altitude` come `***REDACTED***`. L'utente non ha modo di
vederle dall'app. Inoltre le etichette di `print_obs_config` sono stringhe
Italiane hardcoded, quindi non traducibili.

**Cosa fare**

1. Separare i due usi di `print_obs_config`: il dump pensato per log pubblici
   resta redacted, la vista interna dell'app mostra i valori.
   Approccio consigliato: introdurre una funzione dedicata al riepilogo
   leggibile (per esempio `observatory_summary_lines(config) -> list[str]`) che
   restituisce righe già etichettate, e lasciare `print_obs_config` per lo stdout.
   Non cambiare la firma pubblica di `print_obs_config` se un test esistente la
   copre; in quel caso valuta un parametro keyword-only con default `False`.
2. Passare la nuova funzione in `_observatory_summary` e rimuovere l'uso di
   `redirect_stdout`/`io.StringIO` da quella funzione.
3. Sostituire le etichette Italiane hardcoded con chiavi passate da chi chiama,
   oppure usare il meccanismo gettext esistente (`asteroidpy/interface/_intl.py`,
   `_i18n.py`). Le chiavi devono comparire anche in `asteroidpy/locales/*/base.po`
   e negli altri cataloghi: se serve, riusare `scripts/fill_po_gaps.py`.
4. Non stampare mai coordinate in chiaro in un log o in una notifica: la
   redazione va mantenuta nel percorso di logging.

**Criteri di accettazione**

- La schermata Osservatorio mostra latitudine, longitudine e altitudine reali.
- `print_obs_config()` senza argomenti continua a redattare i campi sensibili,
  `show_sensitive=True` li mostra: comportamento coperto da test.
- Le etichette del riepilogo passano per gettext e sono presenti nei cataloghi.
- `docs/source/asteroidpy.rst` riflette la nuova funzione pubblica.

**Verifica** — `pytest -q && ruff check asteroidpy/ tests/ && mypy asteroidpy/ && isort --check asteroidpy/ tests/ && black --check asteroidpy/ tests/`

**Dipende da** — nessuno.

---

## F7 — Esponere i parametri mancanti nelle schermate

**Contesto** — `asteroidpy/interface/_tui_screens.py:580` (`ObservatoryHorizonScreen`),
`:675` (`WeatherScreen`), `:1301` (`BestNightScreen`), `:1157` (`EphemerisScreen`);
`asteroidpy/scheduling.py:1228` (`object_ephemeris`, `number=30` fisso a
`asteroidpy/scheduling.py:1283`), `:1519` (`best_nights`, che accetta già
`max_nights`).

**Problema** — l'utente non può scegliere quanti punti di efemeride ottenere, non
può cambiare il numero di notti dal pannello Miglior notte, e i campi
dell'orizzonte virtuale non vengono precompilati con i valori salvati (a differenza
della schermata coordinate).

**Cosa fare**

1. `object_ephemeris`: aggiungere un parametro `number: int = 30` con
   validazione (intero, `>= 1`, tetto alto sensato, per esempio 10000) e
   propagarlo alla chiamata `MPC.get_ephemeris`. Aggiungere l'input
   corrispondente in `EphemerisScreen`.
2. `BestNightScreen`: aggiungere un input per il numero di notti, validato e
   passato a `best_nights(max_nights=...)`. Ricordare che `best_nights` applica
   già `max(1, max_nights)`: definire in chiaro se l'input ha un limite superiore.
3. `WeatherScreen`: aggiungere almeno l'intervallo orario mostrato (72h di default
   7Timer) e l'unità di temperatura (C/F), entrambe locali alla schermata, senza
   cambiare il contratto di `weather_forecast_report` se non è necessario.
4. `ObservatoryHorizonScreen`: precompilare `#nord`, `#south`, `#east`, `#west`
   dalla configurazione in `on_mount`, con lo stesso pattern già usato da
   `ObservatoryCoordsScreen`. Validare che i valori siano numerici e in 0-90.
5. Tutti i nuovi input devono tradurre le etichette e i messaggi di errore.

**Criteri di accettazione**

- I nuovi campi sono precompilati dove esiste un valore salvato e validati.
- `object_ephemeris` copre `number=1`, il default e un valore non valido, via test.
- I limiti dei nuovi input sono testati come in `ObservingTargetListScreen`
  (notifica di clamping tradotta).

**Verifica** — stesso gate di `F1`.

**Dipende da** — nessuno.

---

## F9 — Editor in-app dei pesi del planner

**Contesto** — `asteroidpy/configuration.py:36` (`SECTION_DEFAULTS`, sezione
`Planner`), `asteroidpy/scheduling.py:47` (`DEFAULT_PLANNER_WEIGHTS`), `:55`
(`DEFAULT_PLANNER_MAX_NIGHTS`), `:1291` (`_planner_settings`); il menu di
configurazione è `asteroidpy/interface/_tui_screens.py:177` (`ConfigRootScreen`) →
`:205` (`GeneralConfigScreen`).

**Problema** — le cinque opzioni `[Planner]` (`max_nights`, `w_cloud`,
`w_seeing`, `w_transparency`, `w_moon`) si possono cambiare **solo editando a
mano** l'INI, mentre le altre undici opzioni hanno un editor nella TUI. L'utente
non può sapere quali pesi sono attivi senza aprire un file di configurazione.
`README.md` lo dichiara esplicitamente come limite noto.

**Cosa fare**

1. Aggiungere `Configuration → Planner` con i cinque campi, precompilati dalla
   configurazione, following the same pattern di
   `Configuration → Observatory → Observatory coords` (prefill in `on_mount`).
2. Mostrare i pesi **normalizzati** come vengono effettivamente usati da
   `_planner_settings` (`:1338-1341`), così l'utente vede `0.4` come `0.40` e una
   somma di pesi grezzi diversa da 1 come pesi relativi coerenti.
3. Validare in ingresso: `max_nights` intero `>= 1`; pesi float finiti e `>= 0`;
   somma `> 0`. Ricalcare esattamente le regole di `_planner_settings` invece di
   duplicarle: se serve, estrai una funzione di validazione condivisa e
   richiamala sia dalla UI sia dal loader.
4. Mostrare l'anteprima dello score su un numero ridotto di notti, usando
   `best_nights` (`asteroidpy/scheduling.py:1519`), così l'effetto dei pesi è
   immediatamente visibile. La preview deve rispettare `--offline`/cache di A3.
5. Aggiungere le funzioni di persistenza in `configuration.py` con lo stesso
   nome delle altre (`change_*`), che chiamano `load_config` + `save_config`.
6. Tradurre ogni stringa e aggiungerla ai cataloghi.

**Criteri di accettazione**

- I cinque valori sono leggibili e modificabili dalla TUI e sopravvivono al
  riavvio.
- Un peso negativo, `NaN`, `inf` o una somma nulla sono rifiutati con un
  messaggio tradotto, non silenziosamente sostituiti dal default.
- La preview dello score cambia quando cambiano i pesi.
- `README.md` (tabella Configuration) e `docs/source/index.rst` non dicono più
  che i pesi sono solo-INI.
- Test: salvataggio, rifiuto dei valori invalidi, normalizzazione mostrata.

**Verifica** — stesso gate di `F1`.

**Dipende da** — nessuno.

---

## F2 — Rimuovere il frontend legacy orfano

**Contesto** — `asteroidpy/interface/_config_menus.py` (188 righe),
`asteroidpy/interface/_schedule_menus.py` (204 righe),
`asteroidpy/interface/_input.py` (40 righe), `asteroidpy/interface/_main.py:17`
(`main_menu`), `asteroidpy/interface/__init__.py:14` (`__all__`).

**Problema** — questi moduli non sono raggiungibili dall'entry point
(`asteroidpy = "asteroidpy:main"` in `pyproject.toml:41` → `interface()` in
`_main.py:35` → solo Textual). Sono già **divergenti** dal TUI: `scheduling_menu`
non ha la voce best-night e non fa il clamping dei range che fa
`ObservingTargetListScreen`. Sono ~430 righe di logica duplicata che marcano
tossicità e divergenza.

**Cosa fare**

1. **Decidere esplicitamente l'esito e registrarlo nel prompt/issue**: di
   default, **rimuovere**. Prima di cancellare, verificare con
   `rg -n "main_menu|config_menu|scheduling_menu|get_integer|get_float|prompt_line|prompt_int_in_range"`
   che nessun altro modulo, test o documento li importi.
2. Rimuovere i file, l'esportazione `main_menu` da `__init__.py`, e le
   dipendenze associate in `_main.py`.
3. Aggiornare la docstring di `asteroidpy/interface/__init__.py` (menziona
   "legacy text menus") e `docs/source/asteroidpy.rst:70-95` (descrive i 7
   sottomoduli privati e `main_menu`).
4. Se invece si preferisce deprecare: mantenere `main_menu` con un avviso
   `DeprecationWarning` e rimandare alla TUI, e **allinearlo comunque** alla
   TUI. Non lasciare due frontend divergenti.
5. Non perdere funzionalità: ogni schermata della TUI deve avere un
   corrispondente, o va dichiarato nella doc cosa è stato perso.

**Criteri di accettazione**

- Nessun riferimento residuo ai moduli rimossi in codice, test, `README.md`,
  `docs/`, `CONTRIBUTING.md`.
- `pytest -q` verde senza rimuovere test che coprivano comportamento utile:
  se un test copre solo i menu legacy, eliminarlo insieme al codice.
- Docs allineate all'esito scelto.

**Verifica** — stesso gate di `F1`, più
`rg -n "main_menu|_config_menus|_schedule_menus|_input\b" .` per confermare la pulizia.

**Dipende da** — nessuno.

---

## F6 — Rimuovere il token CSRF fallback hardcodato

**Contesto** — `asteroidpy/scheduling.py:96`
(`_MPC_WHATSUP_AUTH_TOKEN_FALLBACK`), `:108`
(`_scrape_whatsup_authenticity_token`), `:143`
(`resolve_whatsup_authenticity_token`), chiamato da
`asteroidpy/interface/_tui_screens.py:821`.

**Problema** — un token di autenticità Rails statico è versionato nel sorgente.
Non è un segreto dell'utente, ma è un segreto nel repository, quasi certamente
scaduto, e il suo fallback maschera il fallimento: quando lo scraping fallisce
silenziosamente l'utente vede una lista target vuota senza capire perché.

**Cosa fare**

1. Rimuovere `_MPC_WHATSUP_AUTH_TOKEN_FALLBACK` e il suo uso.
2. `resolve_whatsup_authenticity_token` deve, allo stato `used_fallback=True`,
   restituire un token vuoto e il chiamante deve **segnalare l'errore** invece di
   proseguire: notifica tradotta che dice che il MPC ha risposto in modo inatteso
   e di riprovare più tardi. Nessun output vuoto e silenzioso.
3. Propagare il motivo dello scraping (status HTTP non 200, markup cambiato,
   timeout) in un tipo di errore chiaro, così la UI può distinguerlo da
   "nessun oggetto trovato".
4. Ricordare che questo compito **non** risolve la cache del token: quello è il
   compito A1.
5. Aggiornare i test che oggi verificano il fallback.

**Criteri di accettazione**

- Nessun token o segreto nel sorgente; `rg -n "authenticity_token" asteroidpy/`
  mostra solo scraping del token dalla pagina.
- Un fallimento di scraping produce un messaggio comprensibile, non una tabella
  vuota silenziosa.
- Test per: scraping riuscito, pagina senza token, HTTP non 200, timeout.

**Verifica** — stesso gate di `F1`.

**Dipende da** — nessuno.

---

## A1 — Cache persistente delle risposte di rete

**Contesto** — `asteroidpy/scheduling.py:41` (`SEVENTIMER_API_URL`), `:291`
(`httpx_get`), `:343` (`httpx_post`), `:430` (`weather_forecast_raw`), `:713`
(`observing_target_list_scraper`), `:1039` (`get_neocp_ephemeris`), `:1119`
(`fetch_neocp_json_and_ephemeris`), `:108`
(`_scrape_whatsup_authenticity_token`), `:143`
(`resolve_whatsup_authenticity_token`); `asteroidpy/configuration.py:61`
(`canonical_config_path`); `docs/source/asteroidpy.rst:129` afferma che
`resolve_whatsup_authenticity_token` «caches» i token, ma non lo fa.

**Problema** — ogni esecuzione ricontatta MPC e 7Timer. Il token del form
Rails viene ri-scrapato a ogni run della lista target. Non esiste alcuna cache,
quindi non esiste nemmeno la base per una modalità offline.

**Cosa fare**

1. Aggiungere un modulo dedicato alla cache (per esempio
   `asteroidpy/cache.py`) con una sola responsabilità: mappa
   `chiave → (payload, timestamp)` serializzata su disco.
2. La cache sta nella directory dati utente, non nella config:
   `platformdirs.user_cache_dir("asteroidpy")`. Non aggiungere opzioni INI per il
   percorso.
3. Formato: JSON con metadati, o SQLite. Se SQLite, la dipendenza deve entrare in
   `pyproject.toml` e va valutato il costo per utenti Windows.
4. TTL per classe di dato, non un TTL unico: token del form breve (minuti),
   meteo 7Timer medio (ore), `neocp.json` breve (minuti, è un feed vivo),
   efemeridi lunghe (giorni). TTL come costanti pubbliche documentate.
5. Integrare la cache in **un unico punto** di accesso alla rete, così le
   schermate non devono sapere nulla: le funzioni pubbliche di `scheduling.py`
   mantengono la stessa firma e il ritorno.
6. Distinguere chiaramente **hit**, **miss** e **fallover**: un errore di rete
   con una entry in cache deve restituire la cache con l'indicazione dell'età,
   non `{}` o `[]`.
7. Cache del token CSRF per omnia: fissa il doc drift di
   `docs/source/asteroidpy.rst:129` (diventa vero, o correggi la frase).
8. Aggiungere un modo per svuotare la cache dalla UI (menu Configurazione →
   Generale) e in `# Dati` dell'interfaccia CLI di B1.

**Criteri di accettazione**

- Un secondo run identico non genera richieste di rete (test con
  `monkeypatch` che conta le chiamate a `httpx`/`requests`).
- TTL scaduto forza un refresh; errore di rete con cache valida usa la cache.
- Cache disattivabile e svuotabile; il percorso cache non è quello del file INI.
- La rimozione del file di cache non rompe l'avvio.
- `docs/source/asteroidpy.rst` e `README.md` descrivono cache, TTL e percorso.

**Verifica** — stesso gate di `F1`.

**Dipende da** — `F6` (il token non deve più avere un fallback statico).

---

## A2 — Export dei risultati su file e clipboard

**Contesto** — `asteroidpy/interface/_tui_screens.py:1002` e `:1148` usano
`show_in_browser(jsviewer=True)`; `EphemerisScreen` (`:1157`) non ha l'opzione;
`:1031` (`ResultLogScreen`) è il dump testuale; `asteroidpy/scheduling.py:469`
(`weather_forecast_report`), `:809` (`observing_target_list`), `:880`/`:943`
(`neocp_confirmation`), `:1228` (`object_ephemeris`), `:1579`
(`best_nights_report`).

**Problema** — l'unico export è un HTML temporaneo su 2 schermate su 3. Non
esistono CSV, JSON, né un percorso scelto dall'utente, né copia negli appunti.

**Cosa fare**

1. Aggiungere un modulo di export che trasforma i risultati in
   `QTable`/liste/dicts in CSV, JSON e testo tabellare, con intestazioni e
   formato numerico stabili (UTC esplicito, `delimiter`, `decimal`).
2. Aggiungere un `Input` per il percorso di destinazione su tutte le schermate
   che producono tabelle: lista target, NEOcp, efemeridi, meteo, miglior notte.
   Precompilare con un nome suggerito nella directory dati utente e chiedere
   conferma prima di scrivere.
3. Usare scrittura atomica (temp + `os.replace`), come già fatto in
   `asteroidpy/configuration.py:135` (`_atomic_replace`): riusa quel pattern o
   spostalo in un modulo condiviso e riusalo da entrambi i lati.
4. Rimuovere la scrittura di file temporanei sparsi: `show_in_browser` va
   sostituito dall'export su percorso esplicito, o mantenuto come opzione
   separata e dichiarata.
5. Aggiungere "copia negli appunti" per il contenuto corrente di
   `ResultLogScreen`, con fallback trasparente se il terminale non lo supporta.
6. Trascrivere ogni nuova etichetta nei cataloghi gettext.

**Criteri di accettazione**

- Export CSV e JSON da tutte le schermate tabellari, con test che verificano
  intestazioni, ordine delle colonne e separatori decimali.
- Scrittura atomica: un errore a metà non lascia un file parziale.
- Percorso non scrivibile → messaggio tradotto, nessuna traccia.
- Il JSON di una tabella è ricaricabile e contiene i valori come numeri, non
  come stringhe localizzate.

**Verifica** — stesso gate di `F1`.

**Dipende da** — `A1` (per l'indicazione dell'età del dato in fase di export).

---

## A3 — Modalità offline e surfacing dello stato dei dati

**Contesto** — oggi i fallimenti degradano a testo: `weather_forecast_report`
(`asteroidpy/scheduling.py:479`), `best_nights_report` (`:1590`),
`observing_target_list_scraper` (`:759`), `async_neocp_confirmation` (`:974`).

**Problema** — l'utente non distingue "nessun dato", "rete irraggiungibile",
"MPC ha cambiato la pagina" e "sto guardando una cache vecchia di 3 giorni".

**Cosa fare**

1. Distinguere i tre stati nel ritorno delle funzioni di `scheduling.py`: dato
   fresco, dato da cache (con età), errore (con motivo). Non usare più `{}` /
   `[]` / stringa d'errore per signalling tre casi diversi.
2. Soprattutto: usare le eccezioni per gli errori reali. Le funzioni pubbliche
   che oggi catturano tutto dovrebbero propagare un errore tipizzato
   (`DataSourceError` con `source`, `reason`, `cached_age`), mantenendo un
   wrapper che produce il report testuale per chi lo chiama dalla UI.
3. Banner di stato persistente nella TUI (non una notifica effimera) che dice
   "dati in cache, età 6 h" o "rete non raggiungibile".
4. Una modalità offline esplicita: le schermate di scheduling funzionano
   dichiarando che il dato è in cache; se non c'è cache, falliscono in modo
   comprensibile invece di restituire tabelle vuote.
5. Aggiungere la modalità offline a `# Dati` dell'interfaccia CLI di B1.

**Criteri di accettazione**

- Un errore di rete con cache valida produce un output etichettato, non vuoto.
- Un errore di rete senza cache produce un messaggio con il motivo.
- Il banner resta visibile finché il dato non è fresco.
- Test per: hit fresco, hit da cache, errore senza cache.

**Verifica** — stesso gate di `F1`.

**Dipende da** — `A1`.

---

## B1 — Interfaccia a riga di comando non interattiva

**Contesto** — `pyproject.toml:41` (`asteroidpy = "asteroidpy:main"`);
`asteroidpy/__init__.py:31` (`main`, che oggi chiama solo `interface()`);
`asteroidpy/interface/_main.py:35`; non esiste alcun parsing degli argomenti in
tutto il progetto; non esiste `__main__.py`.

**Problema** — ogni funzionalità è raggiungibile solo dalla TUI. Non c'è
`--version`, non ci sono subcommand, non c'è output machine-readable. Lo
strumento è inutilizzabile in uno script, in un cron, o in CI.

**Cosa fare**

1. Aggiungere `asteroidpy/cli.py` con `argparse` (non introdurre `click`/`typer`
   solo per questo). Entry point: `asteroidpy` per la TUI, `asteroidpy-cli`
   (o `--cli` sulla stessa entry point, ma valuta che `PROFILE` in
   `asteroidpy/__init__.py:26` resti coerente) per il batch.
2. Subcommand, uno per schermata di scheduling: `weather`, `neocp`, `ephemeris`,
   `targets`, `twilight`, `best-night`. Ognuno espone i parametri che oggi
   esistono solo nella TUI (durata, elongazioni, alt minima, numero di oggetti,
   tipo oggetto, passo e numero di punti per l'efemeride, numero di notti).
3. Flag globali: `--version` (da `asteroidpy/version.py`), `--json` (output
   machine-readable, UTC esplicito, chiavi stabili), `--config` (percorso INI
   alternativo, utile ai test), `--offline` (da A3), `--no-color`.
4. `python -m asteroidpy` deve funzionare: aggiungere
   `asteroidpy/__main__.py` che delega alla CLI.
5. I subcommand devono riusare `scheduling.py` e `configuration.py` senza
   duplicare logica e senza importare Textual. Codice di uscita non zero su
   errore, con il messaggio su stderr.
6. Non rompere il workflow TUI esistente e non cambiare il default di
   `asteroidpy` senza nota.

**Criteri di accettazione**

- `asteroidpy --version` e `python -m asteroidpy --version` funzionano.
- Ogni subcommand ha un test con la rete simulata che verifica l'output e il
  codice di uscita.
- `--json` produce output valido e verificabile per ogni subcommand.
- Importare `asteroidpy.cli` non importa Textual.
- `README.md` (sezione Quick Start) e `docs/source/asteroidpy.rst` documentano la CLI.

**Verifica** — stesso gate di `F1`, più un test che verifica l'assenza di
`import textual` nel percorso CLI.

**Dipende da** — `A3` (per `--offline`), `F7` (i parametri esistono già).

---

## D1 — Grafici e curve di visibilità

**Contesto** — `asteroidpy/scheduling.py:469` (report meteo), `:1228`
(`object_ephemeris`), `:1519`/`:1579` (miglior notte); `astropy` è già
dipendenza, `matplotlib` no.

**Problema** — tutti i risultati sono tabelle testuali a larghezza fissa. Non si
vede l'andamento dell'altitudine di un oggetto nella notte, non si vede la
posizione in cielo, non si vede l'andamento del punteggio di una notte.

**Cosa fare**

1. Aggiungere `matplotlib` con backend `Agg` (nessuna GUI, il processo può
   girare su server): backend impostato **prima** di `pyplot`, in un punto
   unico, per non rompere test e ambienti headless.
2. Tre grafici, ognuno come funzione pubblica testabile in un modulo dedicato:
   - curva di altitudine (e azimut) nel tempo per un oggetto;
   - sky plot per la notte, con orizzonte virtuale sovrapposta;
   - barre del punteggio delle notti candidate, con la soglia di precipitazione
     marcata.
3. I dati devono provenire da `scheduling.py`, non da nuove chiamate di rete:
   riusa `object_ephemeris`, `earth_location_from_config`, `is_visible`,
   `best_nights`.
4. `matplotlib` va in un extra opzionale (`pyproject.toml`, es.
   `pip install asteroidpy[plots]`) e la TUI deve offrire i grafici solo se
   l'extra è installato, con un messaggio tradotto che spiega come installarlo.
5. Salvataggio su file con lo stesso dialog di percorso di A2, più anteprima nel
   terminale (`ascii` backend o `Textual` `Static` con rendering testuale
   minimale: non puntare a plot interattivi nel TUI).
6. Rispettare la localizzazione: assi e legende in inglese (le stringhe gettext
   degli schermi restano tradotte).

**Criteri di accettazione**

- `pytest -q` verde **anche** senza `matplotlib` installato (lo import è lazy).
- I tre grafici si generano da dati sintetici in test e producono un file
  non vuoto.
- La TUI segnala in modo chiaro quando l'extra manca.
- `README.md` (tabella Feature) e `docs/source/index.rst` elencano i nuovi grafici.

**Verifica** — stesso gate di `F1`, più
`python -c "import asteroidpy" ` in un ambiente senza `matplotlib`.

**Dipende da** — `A2` (percorso di output condiviso).

---

## C1 — Watchlist oggetti persistente

**Contesto** — nessun catalogo locale esiste; gli oggetti arrivano da
`observing_target_list` (`asteroidpy/scheduling.py:809`), da
`neocp_confirmation` (`:880`) o da una ricerca puntuale con
`object_ephemeris` (`:1228`).

**Problema** — l'utente non può salvare un oggetto che gli interessa, né
ritrovare «quello che volevo vedere giovedì». Ogni risultato è effimero.

**Cosa fare**

1. Persistenza in un file JSON nella directory dati utente
   (`platformdirs.user_data_dir`), con schema versionato e una `schema_version`
   per la migrazione futura. Scrittura atomica (stesso pattern di
   `asteroidpy/configuration.py:135`).
2. Schermata Watchlist: elenco degli oggetti salvati, con designazione, data di
   aggiunta e note libere. Aggiungi/rimuovi con `--` dell'azione e tasto di
   conferma per la rimozione.
3. Pulsante «Aggiungi alla watchlist» su ogni riga delle schermate lista target,
   NEOcp ed efemeridi, non solo un campo di testo manuale.
4. Dalla watchlist: lancio dell'efemeride e visualizzazione delle osservazioni
   registrate (se C3 è già fatto, altrimenti un placeholder chiaro).
5. Nessuna nuova dipendenza; nessuna modifica al file INI `.asteroidpy` (che
   resta la configurazione, non i dati utente).

**Criteri di accettazione**

- Aggiunta e rimozione sopravvivono al riavvio; test con directory temporanea.
- Un file watchlist corrotto non impedisce l'avvio: viene ricreato con avviso.
- `schema_version` presente e testata.
- Traduzioni per ogni nuova stringa.

**Verifica** — stesso gate di `F1`.

**Dipende da** — nessuno.

---

## C2 — Piani di sessione salvati e ripresi

**Contesto** — `asteroidpy/interface/_tui_screens.py:636`
(`SchedulingRootScreen`) è un hub di query **stateless**: ogni schermata
riscrive i propri parametri e nessun risultato sopravvive. `ObservingTargetListScreen`
(`:716`) raccoglie data/ora, durata, elongazioni, tipo oggetto.

**Problema** — non esiste il concetto di piano: non si salva «martedì 21:30, 4
ore, NEAs, elongazione solare > 60°», non si riprende, non si confronta un piano
con il meteo previsto per quella notte.

**Cosa fare**

1. Un piano è: data/ora di inizio, durata, filtri MPC, orizzonte virtuale
   usato, e la lista di target risultante. Persistenza JSON come in C1.
2. Schermata Piani: elenco, duplica, rinomina, elimina; apertura di un piano che
   rilancia la query con i parametri salvati.
3. Collegamento con il meteo: per ogni piano salvato mostra lo score di
   `best_nights` della notte corrispondente, così l'utente vede la qualità del
   cielo previsto senza aprire due schermate.
4. Marcatura dei target come «osservato», con i target previsti dal piano e i
   target effettivamente osservati affiancati.
5. I piani non sono cancellati alla scadenza: sono storico. Avvisa solo se le
   date sono passate.

**Criteri di accettazione**

- Salva, riapre e rilancia una query identica a quella originaria.
- Lo score meteo del piano è quello di `best_nights` per la notte del piano.
- Test di persistenza e di riapertura con directory temporanea.
- Traduzioni per ogni nuova stringa.

**Verifica** — stesso gate di `F1`.

**Dipende da** — `C1` (stesso layer di persistenza dati utente).

---

## C3 — Registro osservazioni ed export ADES-MPC

**Contesto** — oggi lo strumento dice **cosa osservare**, non **cosa è stato
osservato**. Nessun modulo tiene traccia delle osservazioni; `mpc_code` e
`observer_name` sono già in configurazione
(`asteroidpy/configuration.py:261`, `:269`) ma servono solo come parametri di
query.

**Problema** — manca il secondo atto del lavoro dell'astronomo. Questo era già un
TODO del progetto.

**Cosa fare**

1. Registro persistente: per ogni osservazione, designazione dell'oggetto,
   timestamp, filtro/exposizione se disponibili,Seeing, aria di qualità, note.
   Riutilizza la persistenza di C1 (stesso file dati utente, sezione separata).
2. Schermata Registro: inserimento guidato a partire da un oggetto in
   watchlist, elenco filtrabile per oggetto e per intervallo di date, correzione
   e cancellazione.
3. Export in un formato scambiabile con il MPC. Verificare **il formato
   attualmente richiesto** (ADES XML o MPEC formato osservativo) prima di
   implementare: non inventare un formato. Se l'export richiede dati che
   AsteroidPy non raccoglie, produrre il subset disponibile e **dichiarare
   esplicitamente** quali campi non sono popolati, senza valori fittizi.
4. Collegamento con la `mpc_code` configurata e avviso chiaro se è ancora
   `XXX` (il default in `asteroidpy/configuration.py:52`), perché un export con
   codice osservatorio fittizio è inutile al MPC.
5. L'export riusa l'infrastruttura di A2 (percorso, conferma, scrittura atomica).

**Criteri di accettazione**

- Il registro sopravvive al riavvio ed è filtrabile.
- L'export produce un file che supera una validazione del formato scelto
  (test con validatore o con asserzioni sulla struttura).
- I campi non disponibili sono dichiarati, mai inventati.
- Avviso quando `mpc_code` è `XXX`.

**Verifica** — stesso gate di `F1`.

**Dipende da** — `C1`, `A2`.

---

## E1 — Alert programmati e notifiche persistenti

**Contesto** — le uniche notifiche sono toast effimeri di `app.notify()` per
validazione e clamping degli input (es. `asteroidpy/interface/_tui_screens.py:825`,
`:1134`, `:1213`). Nessun meccanismo persistente o programmato.

**Problema** — l'utente deve aprire l'app e interrogare i dati per scoprire che
un oggetto è sorto o che un NEOcp ad alto score è visibile stasera. Erano già un
TODO del progetto.

**Cosa fare**

1. Motore di alert: una regola è (criterio, azione, destinatario). Criteri
   supportati, tutti calcolabili con le funzioni già esistenti in
   `scheduling.py`: oggetto che supera una quota di altitudine, oggetto che
   entra nella finestra di visibilità, NEOcp che supera una soglia di score e i
   filtri dell'utente, score di una notte sopra una soglia.
2. Azioni: notifica interna persistente (coda consultabile nella TUI, non un
   toast che sparisce), email via SMTP, webhook HTTP.
3. Esecuzione: un comando di verifica (una tantum) e un modo pianificato
   (`--due`/`--every` nella CLI di B1, oppure un timer Textual con
   `set_interval`). Scegliere un modello solo e documentarlo; la TUI non deve
   assumersi di girare per sempre.
4. **Nessuna credenziale nel file INI**: SMTP e webhook usano variabili
   d'ambiente, o un file di credenziali con permessi restrittivi nella directory
   dati utente. Non salvare password nel file di configurazione.
5. Rate limiting e deduplica: niente raffica di email per lo stesso oggetto.
6. Rispetta `DEFAULT_REQUEST_TIMEOUT_SEC` e non bloccare il loop TUI: polling in
   un worker.

**Criteri di accettazione**

- Una regola di test viene valutata correttamente e produce un alert una volta
  sola (deduplica verificata).
- Nessuna credenziale in `.asteroidpy` né nel sorgente.
- Il comando una tantum è testabile con la rete simulata e non richiede la TUI.
- Traduzioni per le stringhe della nuova UI.

**Verifica** — stesso gate di `F1`.

**Dipende da** — `B1` (per l'esecuzione pianificata), `C1` (persistenza).

---

## F3 — Test della TUI con `App.run_test()` e pilot

**Contesto** — `asteroidpy/interface/_tui_screens.py` è 1344 righe e **non ha
nessun test**. I 75 test esistenti coprono solo logica pura. Nessun file in
`tests/` importa `_tui_screens`.

**Cosa fare**

1. `tests/test_tui_screens.py` con `pytest-asyncio` (o `anyio`) e il pattern
   `async with app.run_test() as pilot:`.
2. Coprire almeno: composizione di ogni schermata senza eccezioni, `escape`
   torna al menu precedente da ogni schermata, validazione degli input
   (numero non numerico, fuori range), prefill dei campi di C1/F7, e il cambio
   lingua che ricostruisce lo stack (`_refresh_main_menu_after_locale`).
3. Simulare la rete: patchare le funzioni di `scheduling.py` a livello di
   modulo, non i client HTTP. Non colpire mai la rete in un test.
4. Test della navigazione principali: Configurazione → Osservatorio → coordinate
   → salva → riapri e verifica il valore persistito (con directory temporanea
   come in `tests/test_configuration.py`).
5. Attenzione a `asyncio.to_thread` e `run_worker` usati in
   `_tui_screens.py:1061`: i test devono attendere il completamento senza
   `time.sleep` fragili. Preferire un meccanismo di attesa esplicito.
6. Aggiungere `pytest-asyncio` in `pyproject.toml` se assente, con
   `asyncio_mode = "auto"` o marker espliciti coerenti con lo stile esistente.

**Criteri di accettazione**

- `pytest -q` verde e nessun test che tocchi la rete.
- Almeno una copertura per ciascuna delle 19 classi `Screen`.
- `mypy.ini:44-48` continua a ignorare gli errori in `tests.*`: non allargare il
  gate per far passare i test.

**Verifica** — stesso gate di `F1`, più
`pytest -q -k tui` e un controllo che la suite sia offline (es. con
`pytest-socket` o equivalente già presente).

**Dipende da** — nessuno (ma va fatto dopo `F1`/`F7`, che cambiano le schermate).

---

## F4 — Deduplicare i test di configurazione

**Contesto** — `tests/test_configuration.py` (15 test, stile pytest) e
`tests/test_configuration_unittest.py` (13 test, `unittest.TestCase`, caricato
con `importlib.util.spec_from_file_location`) coprono ~90% lo stesso terreno;
`test_configuration_corrupted.py` e `test_configuration_unreadable.py` coprono
un caso ciascuno.

**Cosa fare**

1. Unificare in un solo file pytest-style, mantenendo tutti i casi coperti,
   anche quelli presenti solo in uno dei due (`KeyError` dell'orizzonte, merge dei
   default, non-redazione con `show_sensitive=True`).
2. Rimuovere i file e il caricamento via `importlib`.
3. Considerare di unire anche `corrupted`/`unreadable` come casi parametrizzati
   dello stesso test di caricamento, senza perdere copertura.
4. Se si preferisce mantenere `unittest` per una ragione precisa, dirlo in un
   commento; altrimenti una sola suite pytest.
5. Aggiungere il test mancante per `get_observatory_coordinates`
   (`asteroidpy/configuration.py:242`), con la rete simulata: è l'unica funzione
   di configurazione che richiede rete e nessun test la copre.

**Criteri di accettazione**

- Nessun test perso: il numero di casi coperti non diminuisce.
- `pytest -q` verde, un solo file di test per la configurazione.
- Nessuna perdita di copertura verificabile con il report già disponibile.

**Verifica** — stesso gate di `F1`.

**Dipende da** — nessuno.

---

## F5 — Stage docs e matrix Python nel `Jenkinsfile`

**Contesto** — `Jenkinsfile`: c'è lo stage `Lint`, i test e SonarQube, ma
**nessuno stage docs**, quindi il drift della documentazione non viene
intercettato. La matrix dei test non esercita le versioni dichiarate: il
`Jenkinsfile` usa un singolo `python3` non pinnato, mentre `README.md` dichiara
supporto 3.11, 3.12, 3.13, 3.14 e `pyproject.toml` li elenca nei classifier.
`docs/source/conf.py:91` imposta `nitpicky = True`.

**Cosa fare**

1. Aggiungere uno stage `Docs` che installa `pip install -e ".[docs]"` e lancia
   `(cd docs && make html)` con `-W` (warnings come errori), dato che
   `nitpicky = True` tratta ogni cross-reference rotto come warning. Pubblicare
   `docs/build/html` come artefatto, coerente con `dist/*` e `coverage.xml`.
2. Aggiungere una matrix `3.11, 3.12, 3.13, 3.14` per lint e test, oppure almeno
   per i test, assicurandosi che le versioni richieste siano effettivamente
   disponibili sull'agente Jenkins.
3. Non reintrodurre workflow GitHub Actions: la CI è Jenkins (vincolo esplicito
   di `AGENTS.md`).
4. Aggiornare `CONTRIBUTING.md` e `AGENTS.md` con i comandi e gli stage nuovi,
   mantenendo i due file consistenti come richiesto.
5. Se una versione non è ancora installabile sull'agente, non dichiarare il
   supporto: o si installa, o si rimuove il classifier e la promessa dal README.

**Criteri di accettazione**

- Lo stage docs fallisce su un cross-reference rotto (verificabile rompendone uno
  appena e vedere il fallimento, poi ripristinando).
- La matrix copre tutte le versioni dichiarate nei classifier.
- `AGENTS.md` e `CONTRIBUTING.md` descrivono i comandi e gli stage aggiornati.

**Verifica** — esecuzione locale di `pytest -q`, del gate di lint, e
`(cd docs && make html)` pulito.

**Dipende da** — nessuno, ma farlo dopo le feature che toccano la documentazione
(si rischierebbe di segnalare come fallimento il drift prodotto da quel task).

---

## F8 — Retry con backoff e gestione degli errori di rete

**Contesto** — `asteroidpy/scheduling.py:44` (`DEFAULT_REQUEST_TIMEOUT_SEC = 30.0`)
è l'unico controllo di rete dell'intero progetto. Non c'è retry, non c'è backoff,
non c'è rispetto di `Retry-After`. I client sono tre: `requests`
(`:453`, `:751`), `httpx` (`:320`, `:371`, `:1085`). Gli errori si degradano in
silenzio a `{}`, `[]` o stringhe (`weather_forecast_report:479`,
`best_nights_report:1590`).

**Problema** — un timeout transitorio o un 503 del MPC producono una tabella
vuota senza diagnosi; l'utente non distingue «nessun oggetto» da «richiesta
fallita».

**Cosa fare**

1. Un unico wrapper HTTP con retry esponenziale + jitter, rispetto di
   `Retry-After`, e tetto sui tentativi. I tre call site passano da quel wrapper.
   Non ritentare su 4xx (eccetto 429): ritentare un 400 spreca tempo.
2. Distinguere gli errori tipizzati (`DataSourceError` con `source`, `reason`,
   `status`) invece di `except requests.RequestException: return {}`. Vedi A3: i
   due task devono restare coerenti nella firma delle funzioni pubbliche.
3. Non ritentare mai i POST non idempotenti senza pensarci: `confirmeph2.cgi` e il
   form What's Observable vanno valutati singolarmente.
4. Backoff rispettoso del server: nessun test che introduca sleep reali (usare
   l'iniezione di un sonno fittizio o `unittest.mock`).
5. Esporre un `--timeout` e un `--retries` nella CLI di B1; in TUI mostrare
   "tentativo 2 di 3" invece di un blocco silenzioso.

**Criteri di accettazione**

- Test con un server simulato che fallisce N volte e poi va a buon fine: le
  chiamate effettive sono N+1 e il risultato è corretto.
- Un 4xx non viene ritentato.
- Nessun `sleep` reale nei test: la suite resta veloce.
- Il motivo dell'errore arriva alla UI in forma tradotta.

**Verifica** — stesso gate di `F1`.

**Dipende da** — `A1`, `A3`, `B1` (per i flag), `F6`.
