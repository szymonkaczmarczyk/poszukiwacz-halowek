# Shoe finder

[Polski](README.md) · **English**

Searches shops and marketplaces that ship to Poland for a chosen shoe model in a given size. Results are sorted from
cheapest, and euro prices are converted at the NBP (National Bank of Poland) rate. The tool and its interface are in
Polish.

You pick what to search for from the **model catalog** (`katalog/`): brand, model and size from 38 to 46. The catalog
holds indoor football shoes (Polish: *halówki*) from six brands:

* Munich: Continental, Continental V2, Gresca, G-3, Arenga, One, Debut, Rondo
* Joma: Top Flex, Mundial, Gambeta, Dribling, Maxima
* Nike: Tiempo Streetgato, Tiempo Reactgato, Phantom (IC versions), Gato, Lunargato II
* Adidas: Super Sala III, Top Sala II, F50 and Predator (IN versions)
* Mizuno: Morelia Sala

By default the program searches for Munich Continental in size 41.

## Getting started

```bash
py -m pip install -r requirements.txt
```

```bash
py szukaj.py
```

```bash
py szukaj.py --marka joma --model top-flex --rozmiar 42
```

```bash
py szukaj.py --lista-modeli
```

When it finishes, the terminal shows a list with links, and the browser opens the report
`wyniki/<brand>-<model>/<size>/raport.html` with filters. The same data also goes to `oferty.csv` (Excel) and
`oferty.json` in the same folder.

Useful options:

| Option | What it does |
|---|---|
| `--marka joma` | brand from the catalog (default `munich`) |
| `--model top-flex` | model from the catalog (default `continental`), a name as in `--lista-modeli` or plain, e.g. `"top flex"` |
| `--lista-modeli` | shows brands, models and sizes from the catalog |
| `--profil FILE` | your own `.toml` profile file instead of a catalog model |
| `--rozmiar 42` | EU size (default 41), several comma-separated, e.g. `41,42`, searches each in turn |
| `--max-cena 300` | only offers up to PLN 300 |
| `--tylko-pewne` | only offers with confirmed size availability |
| `--zrodla vinted,olx` | only selected sources (`--lista-zrodel` shows all) |
| `--odswiez` | skips the cache and fetches everything again |
| `--odkrywaj` | searches Google for new shops right away, without waiting a week |
| `--ukryj "LINK"` | hides an offer in later results (several links allowed) |
| `--pokaz-ukryte` | also shows hidden offers |
| `--reset-blokad` | lifts host pauses set after anti-bot protection was detected |
| `--widoczna-przegladarka` | shows the browser windows used for OLX and Goalinn |
| `--nie-otwieraj` | doesn't open the HTML report |
| `-v` | more detail while running |

## Model catalog

Every brand has a file in `katalog/` (e.g. `katalog/joma.toml`), and `katalog/wspolne.toml` holds settings shared by
all of them: the size list, Vinted size numbers, eBay categories and shops that search by phrase (Sportano,
Revealsport, Gain Control).

A search profile has three levels, from general to specific: shared, brand, model. Merging rules:

* `wykluczenia` (exclusions), `kody_wykluczone` (excluded codes) and `nie_dotyczy` (not applicable) add up (e.g. Joma
  excludes turf shoes for every model, and Top Flex also excludes Rebound)
* sections like `[vinted]` or `[olx]` merge field by field
* `[[sklep]]` entries add up, and a shop with the same name on a lower level replaces the higher one
* other fields from a lower level replace higher ones
* `inne_modele_marki` (other models of the brand) is built automatically from the brand's other models and the
  `inne_modele` list in the brand file

A brand file has profile fields (without `model`) and a list of `[[model]]` entries. Each model has an `id` (used in
`--model` and in the data folder name), `model` (words that must be in the title) and optionally `nazwa` (name) and any
profile fields. Model sections are written as `[model.olx]`, `[[model.sklep]]` and so on. Without `frazy` (phrases) the
program uses "brand model" and "halowki brand model".

Nike and Adidas make the same models for different surfaces, so their files have `oznaczenia_hali` (indoor markers):
patterns like `\bic\b`, `\bin\b`, "halówki", "futsal". An offer with the model name but without such a marker goes to
review instead of the confirmed list. Models that are indoor by nature (Gato, Top Sala, Super Sala) have
`oznaczenia_hali = []`.

Rules for models other than Munich Continental and Joma Top Flex are simple for now: name, surface exclusions and a
list of the brand's other models. Product codes are worth adding only after checking them against real offers.

## Your own profile

A model outside the catalog can be described in a separate file and run with `--profil file.toml`. A minimal profile
is enough to work:

```toml
marka = "Joma"
model = "Top Flex"
rozmiar = "42"
wykluczenia = ['rebound', '\bjr\b', 'junior']
```

The program then builds search phrases on its own ("joma top flex"), finds the brand on Vinted by itself and uses the
default manual links. Every extra piece of information improves accuracy.

| Field | Meaning |
|---|---|
| `nazwa` | name in the report (default brand + model) |
| `marka`, `model` | **required**, an offer must contain the brand and all words of the model |
| `rozmiar` | EU size |
| `aliasy_marki` | other spellings of the brand, e.g. `["munchen"]` for Munich |
| `frazy` | search phrases, the first one is the main one |
| `opis_wykluczen` | a short note for the report, e.g. "no V2 and Premium" |
| `wykluczenia` | patterns of versions you don't want (e.g. `'\bv\s?2\b'`, `'rebound'`) |
| `kody_modelu` | patterns of the wanted model's product codes, a code decides even without a name |
| `kody_wykluczone` | patterns of other versions' codes |
| `inne_modele_marki` | names of the brand's other models, a listing with such a name is rejected |
| `nie_dotyczy` | words that mean completely different products (e.g. Continental tires) |
| `oznaczenia_hali` | patterns marking the indoor version (e.g. `'\bic\b'`), without them an offer with the model name goes to review |
| `slowa_kategorii` | words like "halówki", "futsal", a listing without the model name goes to "to review" only with such a word |
| `[[wskazowki]]` | hints from the listing description: `wzorzec` (pattern), optionally `oprocz` (except), `werdykt` (`odrzuc` reject or `sprawdz` review), `opis` |
| `wskazowka_zdjec` | a hint in the report on how to tell the model apart in a photo |
| `[vinted]` | `marka_id` (if empty, the program finds it), `katalog_obuwia`, `rozmiary` (e.g. `{ "41" = 782 }`) |
| `[olx]` | `zapytania`: a list of `["phrase-in-url", page_count]` pairs |
| `[allegro_lokalnie]`, `[ceneo]` | custom `frazy` for these services |
| `[ebay]` | `zapytanie` (query), `kategorie` (default: sports and indoor shoes) |
| `[futbolemotion]`, `[rgol]` | `zapytanie` in the shop's search |
| `[goalinn]` | `lista`: the product list URL in Goalinn, without it Goalinn is skipped |
| `[odkrywanie]` | `frazy` for Google: `["phrase {rozmiar}", "country", "language"]` |
| `[minimalne_odczyty]` | minimum number of items read per source (for failure detection) |
| `[[sklep]]` | a shop: `nazwa`, `lista` (list or search URL), `wzor_linku` (product URL pattern), optionally `wysylka`, `max_produktow`, `dostawa_szacunkowa`, `uwagi` |
| `[[reczny]]` | a link for manual checking: `nazwa`, `url`, `opis`, optionally `bez_klucza = "ebay"` |

URLs and phrases can use the variables `{fraza}`, `{fraza_url}`, `{fraza_z_rozmiarem_url}`, `{rozmiar}`, `{marka}` and
`{model}`.

Patterns are regular expressions in single quotes (`'...'`), matched against lowercase text with Polish characters
stripped ("halówki" is compared as "halowki").

**Result quality depends on the profile.** For Munich Continental the profile knows the product codes and tells the
classic apart from the V2. For a new model it's worth adding exclusions for similar versions (kids', turf, "Pro"
versions etc.), otherwise they end up on the list.

Every model has its own price history, discovered shops and source stats (`dane/profile/<brand>-<model>/`) and a
separate report for each size (`wyniki/<brand>-<model>/<size>/`). The page cache and request limits are shared, so two
profiles don't double the traffic to the same sites.

## Browser interface (Szatnia)

Szatnia ("the locker room") walks you through four steps: brand, model, size (several allowed) and filters (price with
PLN 200, 300, 400 and 500 thresholds, confirmed size only, fresh data, source selection). While scrolling, a bar with a
summary and a "Search offers" button is pinned to the bottom of the screen (shortcut Ctrl ↵, ⌘ ↵ on Mac). At the end of
the filters the bar smoothly docks into the page as a normal element, and after scrolling up it returns to the bottom
of the screen. Your selection stays in the browser after a refresh.

Several sizes at once are consecutive passes of the same search. Most pages from the first pass are already cached, so
the second size runs several times faster (in a test: 42 in 35 s, 43 in 10 s).

During a search you see a progress bar, the status of each source and offers that stream in as soon as a source
finishes. In the 3D scene each source is a glowing sphere orbiting the shoe: it pulses while checking, then changes
color (green done, yellow paused or suspicious, red error). "Stop searching" (or Esc) stops everything within about a
second, also during the pauses between requests. Results from sources that finished are saved.

Results come in three groups (confirmed size, size to check, model to check in the photo), with a tab per size, a
source filter, sorting and pagination by 12. Above the list there is a "Since the last check" block (new, cheaper, more
expensive, gone), and cards have "new" and "PLN X cheaper" badges. The "Hide" button hides an offer right away and saves
it to `ukryte.txt`, and a notification lets you undo it. At the end there are links to pages you need to check by hand.

Only the administrator can add custom models. First set a password (stored as an argon2 hash in `.env`):

```bash
py serwer.py --ustaw-haslo
```

Then log in at `/admin.html`. After logging in, an "Add your own model" button appears in the "Model" step. Login is
limited to 5 attempts per 15 minutes, and the session lasts 12 hours (HttpOnly, SameSite=Strict cookie). Without
logging in the server rejects adding and removing models.

You add a model outside the catalog with the "Add your own model" button in the "Model" step. You enter the brand
(new ones too), the model name and words to skip, e.g. rebound or jr, with ready suggestions. The model goes straight
into the catalog and can be searched. Custom models are stored in `dane/wlasne_modele.json` and are removed in the same
dialog, with confirmation.

The selection is stored in the page URL, e.g. `?marka=nike&model=tiempo&rozmiar=43,44`, so a link opens that model and
those sizes right away.

**The simplest way (one server):** build the interface once, then run only the server. The page will be at
`http://127.0.0.1:8765`.

```bash
cd interfejs
```

```bash
npm install
```

```bash
npm run build
```

```bash
cd ..
```

```bash
py serwer.py
```

**When working on the interface** (live preview of changes) you need Node.js 20 or newer. Start the API server first,
then in a second terminal:

```bash
cd interfejs
```

```bash
npm install
```

```bash
npm run dev
```

The interface runs at `http://127.0.0.1:5190` and forwards `/api` requests to the server on port 8765. End-to-end tests
(desktop and phone, they start both servers themselves, and the search is mocked so they don't query any shops):

```bash
npm run test:e2e
```

Next to the steps there is a 3D scene (Three.js): a stylized shoe built in code, with no third-party models or logos.
Colors change to match the chosen brand, the shoe bounces when the brand changes, and the camera moves with each step.
In the "Size" step the camera looks down at a 38-46 ruler, and the shoe's toe points at the largest selected size. The
scene loads separately, after the page is shown. With "reduce motion" in the system and in browsers without WebGL, a
flat drawing of the shoe stays instead.

### A real 3D shoe model

The scene shows real models: a random one at start, a random one from the brand after choosing a brand, and the line's
own model after choosing a line. The stylized shoe stays only when there are no GLB files at all (e.g. in a fresh copy
of the repository).

Instead of the stylized shoe the scene can show a real model. All it needs is an
`interfejs/public/modele/<brand>-<model>.glb` file, e.g. `munich-continental.glb`. These files are in `.gitignore`
because they are made from private photos. The server detects the file on its own, and the scene loads it after that
model is selected. The program positions the shoe itself: rotates it lengthwise, scales it to the length of a size 42,
puts it on the floor and flips it if the heel ended up in front. Models without a file and broken files get the
stylized shoe.

The model is made from your photos (an AI generator). How to take them:

1. One shoe, clean, laces tied evenly.
2. A plain, contrasting background (light for a dark shoe, dark for a light one), daylight, no flash and no harsh
   shadows.
3. Four photos at shoe height, from the same distance: outer side, inner side, front (toe) and back (heel).
4. The whole shoe in frame, filling about 70% of the photo, sharp, no hands or other objects.
5. Full-resolution photos (JPG or PNG) in `models/<brand>/<model>/`, e.g. `models/munich/continental/` or
   `models/nike/phantom/`. Folders for all catalog models already exist. The whole `models/` folder is in `.gitignore`.

### Generating 3D models from photos

The `narzedzia/modele3d/generuj.py` tool sends selected photos of each model (listed in `wybor_zdjec.json`, only shots
of a single shoe, no pairs or on-foot photos) to the TRELLIS generator on Hugging Face. It removes the background that
the generator recreates under the shoe as a "floor", compresses the file (meshopt and WebP textures, about 130-280 KB)
and saves it in `interfejs/public/modele/`. It skips finished models, so it can run daily until all of them are done.

Put a Hugging Face token (Read type, from huggingface.co/settings/tokens) in `.env` as `HF_TOKEN=...`. A free account
allows about 5 models a day, and a PRO account about 25 GPU minutes a day.

```bash
python3.12 -m venv narzedzia/modele3d/.venv
```

```bash
narzedzia/modele3d/.venv/bin/pip install -r narzedzia/modele3d/requirements.txt
```

```bash
narzedzia/modele3d/.venv/bin/python narzedzia/modele3d/generuj.py
```

A single model: `generuj.py nike/gato`. Regenerating an existing one: `--od-nowa`. List of missing ones: `--brakujace`.

On the author's computer a daily macOS job `pl.szatnia.modele3d` runs
(`~/Library/LaunchAgents/pl.szatnia.modele3d.plist`). Every day at 2:00 (or after the computer wakes up) it runs
`narzedzia/modele3d/codziennie.sh`, which generates missing models until the daily limit runs out. After the last model
is done, the job removes itself. The run is logged in `narzedzia/modele3d/generuj.log`. To turn it off earlier:

```bash
launchctl bootout gui/$(id -u)/pl.szatnia.modele3d
```

```bash
rm ~/Library/LaunchAgents/pl.szatnia.modele3d.plist
```

## API server (for the browser interface)

```bash
py serwer.py
```

The server runs only locally at `http://127.0.0.1:8765`. A description of all endpoints, with the option to try them
out, is at `/api/dokumentacja`.

| Method and path | What it does |
|---|---|
| `GET /api/zdrowie` | whether the server is up and the id of the running search |
| `GET /api/katalog` | sizes, brands and models from the catalog |
| `GET /api/katalog/{marka}/{model}/zrodla` | sources for a model and whether they are available (e.g. eBay without a key is not) |
| `GET /api/katalog/{marka}/{model}/wyniki/{rozmiar}` | the last saved results (`oferty.json`) |
| `POST /api/wyszukiwania` | starts a search, replies `202` with an `id`, or `409` when another one is running |
| `GET /api/wyszukiwania/{id}` | status and finished results for each size |
| `GET /api/wyszukiwania/{id}/zdarzenia` | live progress (Server-Sent Events) |
| `POST /api/wyszukiwania/{id}/przerwij` | stops the search, the current size ends with partial results, the next ones are skipped |
| `POST /api/ukryte` | hides an offer, body `{"url": "..."}` |
| `POST /api/ukryte/przywroc` | unhides an offer, body `{"url": "..."}` |
| `GET /api/admin` | whether the browser is logged in as the administrator |
| `POST /api/admin/logowanie` | administrator login, body `{"haslo": "..."}` |
| `POST /api/admin/wylogowanie` | logout |
| `GET /api/wlasne` | list of custom models |
| `POST /api/wlasne` | adds a custom model (administrator only), body `{"marka", "model", "wykluczenia", "opis", "wymagaj_oznaczenia_hali"}` |
| `DELETE /api/wlasne/{marka}/{model}` | removes a custom model (administrator only) |

Example of starting a search for two sizes in two sources:

```bash
curl -X POST http://127.0.0.1:8765/api/wyszukiwania -H "Content-Type: application/json" -d "{\"marka\": \"nike\", \"model\": \"tiempo\", \"rozmiary\": [\"42\", \"43\"], \"zrodla\": [\"vinted\", \"r-gol\"]}"
```

Fields: `marka`, `model`, `rozmiary` (38-46, up to 9 at once) and optionally `zrodla`, `max_cena`, `tylko_pewne`,
`odswiez`, `reset_blokad`, `pokaz_ukryte`. Other fields are rejected. Only one search runs at a time, because they all
share the same request limits to sites.

Stream events have consecutive `id`s, so after a dropped connection the browser resumes where it left off (the
`Last-Event-ID` header or `?od=`). Event types:

| Type | When | Key data |
|---|---|---|
| `wyszukiwanie_start` | at the start | `rozmiary` |
| `start` | a size starts | `rozmiar`, `zrodla`, `wstrzymane_hosty` |
| `zrodlo_start` | a source starts | `zrodlo` |
| `log` | a source message | `zrodlo`, `tekst` |
| `zrodlo_koniec` | a source finished | `status`, `ofert`, `odczytano`, `oferty` (already priced in PLN) |
| `koniec` | a size is done | `wyniki` in the `oferty.json` format |
| `blad` | the search stopped with an error | `komunikat` |
| `przerywanie` | after a stop request | none |
| `wyszukiwanie_koniec` | always at the end | `stan` (`gotowe` done, `przerwane` stopped or `blad` error) |

The server accepts only `localhost` and `127.0.0.1` hosts (DNS rebinding protection), rejects requests sent from other
sites (the `Origin` header) and adds security headers, including a Content-Security-Policy. If `interfejs/dist` exists,
the server also serves the page, and unknown paths get a custom 404 page.

The site has a privacy policy and terms (`interfejs/polityka-prywatnosci.html`, `interfejs/regulamin.html`), a favicon,
a 1200x630 Open Graph image (`interfejs/public/og.png`), `robots.txt` and `sitemap.xml`. The `[[...]]` fields
(administrator details, domain) must be filled in before sharing the site with others.

## Tests

They check that every catalog model builds a valid profile in every size, that the rules recognize typical offer
titles, and the whole API with the event stream on a mocked engine (no internet connection):

```bash
py -m unittest discover -s testy -t .
```

## Sources

| Source | Method | Size |
|---|---|---|
| Vinted (shipping via Vinted) | catalog page, brand filter | from the "Size" field |
| OLX | a real Chrome browser (Playwright) | from the title, or from the listing description when missing |
| Ceneo (Polish shop price comparison) | product pages | size and price next to shop offers |
| Goalinn / Tradeinn (Spain, ships to PL) | a real Chrome browser, picks the size and reads its price | list of available sizes |
| R-GOL | the shop's search API (Luigi's Box) | list of available sizes |
| Fútbol Emotion (Spain, ships to PL) | the shop's search API | list of available sizes |
| Shops from the profile (e.g. Sportano, Revealsport, Redbox, the brand's official shop) | product pages | size availability from product variants |
| Allegro Lokalnie | results page | from the title or description |
| eBay (DE, ES, IT, FR, GB) | official API, footwear categories only, only with shipping to PL | from the title or listing attributes |
| Discovery (Google via SerpAPI) | once a week, phrases in several languages, found product pages are checked daily | size availability from product data |

Allegro, Decathlon, Zalando, Amazon (and eBay without an API key) block bots (DataDome, Cloudflare, Akamai). The
program doesn't get around them: the report has ready links for manual checking, sorted from cheapest where possible.

In Goalinn the price depends on the size and changes even several times a day, so it may differ by a few złoty from
the one in the report. Goalinn and OLX run through a real browser, and each has its own Chrome profile in
`dane/profil_przegladarki`.

The product page parser reads shops' structured data (JSON-LD, including split into fragments and separate per size)
and common size picker layouts: PrestaShop (lists and buttons), Magento, WooCommerce and size buttons with an
unavailable marker.

## How the program protects your IP from being blocked

* **One request at a time per site.** Different shops are checked in parallel, but requests to one host go one by one.
* **Pauses with random jitter.** By default 7-12 s between requests to the same host, 11-19 s for OLX, 9-15 s for
  Vinted. Settings are in `szukacz/ustawienia.py` (`LIMITY`).
* **A request limit per run.** Each host has a maximum number of requests per run (e.g. Vinted 16, OLX 18, Goalinn 22),
  so the program doesn't comb through sites endlessly.
* **A 6-hour cache.** Running again doesn't download the same pages, it uses the copies in `dane/cache`.
* **Pauses remembered between runs.** The time of the last request to a host is saved in `dane/stan_hostow.json`, so a
  quick rerun waits too.
* **Respecting server signals.** On HTTP 429/503 the program honors the `Retry-After` header and slows down. When
  anti-bot protection is detected (captcha, 403) it stops querying that host for 12 hours instead of trying again. An
  API rejecting a key (e.g. eBay) is not treated as a block.
* **A consistent identity.** One session with cookies per host and a fixed set of browser headers.

## What the report shows

At the top there is a **"Since the last check"** block: new offers, cheaper, more expensive and those that disappeared.
Disappearing offers are counted only from sources that worked correctly this time, so a site failure doesn't look like
the shoes selling out.

Below, offers are split into three groups:

1. **Confirmed size**: the model definitely matches, and the shop or listing confirms the size.
2. **Size to check**: the model matches, but the page doesn't state the size clearly.
3. **Brand in that size, model to check in the photo**: used shoes of the brand without the model name in the title
   (e.g. "halówki Munich 41"). Photos in the HTML report are bigger here.

## How the program recognizes the model

The order of checks, from most certain:

1. **Profile exclusions:** an offer with the name of an excluded version is rejected.
2. **Product codes:** a code of another version rejects the offer, and a code of the wanted model confirms it.
3. **Model name:** all words of the model must be in the title.
4. **The brand's other models:** the name of another model rejects the offer.
5. **Listing description** (Vinted, OLX, Allegro Lokalnie), when the title doesn't state the model: the same set of
   rules plus hints from the profile.

Example from the Munich Continental profile:

| Signal | Continental (classic) | V2 |
|---|---|---|
| Product code | 4100xxx, e.g. 4100944, 4100958 | 4104xxx, 4770xxx |
| Name | "Continental" + a 3-digit color, e.g. 944, 973 | "V2", "V 2", "Continental II" |
| Material in the description (hint only) | leather, suede, kangaroo leather | synthetic, microfiber, polyester |

## Hiding offers

* **In the HTML report** the "hide" button hides the offer right away and copies a command to the clipboard that hides
  it in the terminal too.
* **In the terminal:**

  ```bash
  py szukaj.py --ukryj "https://link-to-offer"
  ```

Hidden links are in `ukryte.txt` (one link per line), shared by all profiles. To restore an offer, remove its line from
this file. The file is in `.gitignore`.

## Prices and shipping

The price in the report includes shipping. Where the shipping cost comes from, from most certain:

* **The cost stated by the shop** (e.g. Revealsport PLN 14.99, Sportano from product data).
* **A price list:** Fútbol Emotion, standard shipping to PL PLN 35.02.
* **An estimate marked "~" and "(szac.)":** Vinted about PLN 18, OLX with OLX Shipping about PLN 15, Polish shops about
  PLN 15.

Goalinn and foreign shops don't state the shipping cost to PL, so their prices are without shipping. Estimates for
fixed sources are in `szukacz/ustawienia.py` (`WYSYLKA_SZACUNKOWA`, `None` means "don't add"). For shops from the
profile there is the `dostawa_szacunkowa` field.

Vinted prices include the buyer protection fee. On Ceneo the program takes the price of the cheapest offer where the
shop listed the wanted size. If none did, it takes the product's lowest price and marks it.

## Discovering new shops (SerpAPI)

This module searches Google for shops the program doesn't know. Phrases in several languages come from the profile
(`[odkrywanie]`), and without them the program uses the main phrase with the size for Poland, Germany, Spain, Italy,
France and the UK. Every page found goes through the same parser as the shops.

* **The search** runs once a week per profile (6-7 queries). That fits in the free SerpAPI plan.
* **Found pages** are remembered and checked on every run (up to 25 pages).
* **Pages that are not products** are skipped until the next weekly search.
* **What is skipped:** services and shops handled separately, banned shops, social networks, aggregators and non-EU
  domains.
* **Shipping:** a shop with a .pl domain gets shipping "yes". For foreign shops the report says "check whether the shop
  ships to PL" and doesn't add their shipping cost.

Setup:

1. Create a free account at https://serpapi.com and copy the API key from the **Api Key** tab.
2. Put it in `.env`:

   ```
   SERPAPI_KEY=your-key
   ```

SerpAPI requests are not cached, because the request URL contains the key.

## Why there are no foreign Vinted versions

Vinted splits countries into regions, and you can only buy within your own region. Spain is in the western region,
Poland in the central-eastern one. A test confirmed they are two separate markets: vinted.es had 96 Munich Continental
listings, vinted.pl 21, and none overlapped. From a Polish account you can't buy directly from vinted.es, so the
program doesn't search that source.

## Banned sites

Offers from domains listed in `ZBANOWANE_HOSTY` in `szukacz/ustawienia.py` are skipped in all profiles, whatever the
source (currently: taternik-sklep.pl).

## Source failure detection

Every source reports how many items it read from the page at all, regardless of how many match. The program
remembers these numbers separately for each profile and marks a source as **suspicious** when:

* it reads fewer than the minimum from `[minimalne_odczyty]` in the profile, or
* it reads less than 30% of its typical number from previous runs.

A warning then appears at the top of the report. No results from such a site most likely means its layout changed, not
that the shoes are gone.

## eBay (optional)

1. Create a free account at https://developer.ebay.com and create a "Production" key.
2. In the `.env` file in the project root, put the keys after the `=` sign, without quotes:

   ```
   EBAY_CLIENT_ID=your-app-id
   EBAY_CLIENT_SECRET=your-cert-id
   ```

   `.env` is in `.gitignore`, so the keys won't reach the repository. `.env.przyklad` is the empty template for the
   repository.

Of the three IDs eBay shows, two are needed: **App ID (Client ID)** as `EBAY_CLIENT_ID` and **Cert ID (Client Secret)**
as `EBAY_CLIENT_SECRET`. The Dev ID is not used.

If the program reports `invalid_client`, the Production key is most likely inactive. eBay disables new Production keys
until the app meets the "Marketplace Account Deletion" requirement:

1. Go to developer.ebay.com, then **Application Keys**.
2. Next to the Production key click the **Marketplace Account Deletion** link.
3. Turn on **Exempted from Marketplace Account Deletion**, choose the reason "I do not persist eBay data" and confirm.
   Leave the notification URL, email and token fields empty.

The program doesn't store eBay API responses on disk, so this declaration is true.

## License

[MIT](LICENSE) © 2026 Szymon Kaczmarczyk

The code is MIT licensed. When using shops, marketplaces and APIs (eBay, SerpAPI), follow their terms.
