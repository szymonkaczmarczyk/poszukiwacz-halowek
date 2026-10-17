# Poszukiwacz obuwia

Szuka wybranego modelu butów w podanym rozmiarze w sklepach i na marketplace'ach z wysyłką do Polski. Wyniki sortuje od najtańszych, a ceny w euro przelicza po kursie NBP.

Co szukać, wybierasz z **katalogu modeli** (`katalog/`): marka, model i rozmiar od 38 do 46. W katalogu są halówki sześciu marek:

* Munich: Continental, Continental V2, Gresca, G-3, Arenga, One, Debut, Rondo
* Joma: Top Flex, Mundial, Gambeta, Dribling, Maxima
* Nike: Tiempo Streetgato, Tiempo Reactgato, Phantom (wersje IC), Gato, Lunargato II
* Adidas: Super Sala III, Top Sala II, F50 i Predator (wersje IN)
* Mizuno: Morelia Sala

Domyślnie program szuka Munich Continental w rozmiarze 41.

## Uruchomienie

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

Po zakończeniu w terminalu pojawia się lista z linkami, a w przeglądarce otwiera się raport `wyniki/<marka>-<model>/<rozmiar>/raport.html` z filtrami. Te same dane trafiają też do `oferty.csv` (Excel) i `oferty.json` w tym samym katalogu.

Przydatne opcje:

| Opcja | Działanie |
|---|---|
| `--marka joma` | marka z katalogu (domyślnie `munich`) |
| `--model top-flex` | model z katalogu (domyślnie `continental`); nazwa jak w `--lista-modeli` albo zwykła, np. `"top flex"` |
| `--lista-modeli` | pokazuje marki, modele i rozmiary z katalogu |
| `--profil PLIK` | własny plik profilu `.toml` zamiast modelu z katalogu |
| `--rozmiar 42` | rozmiar EU (domyślnie 41); kilka po przecinku, np. `41,42`, szuka po kolei w każdym |
| `--max-cena 300` | tylko oferty do 300 zł |
| `--tylko-pewne` | tylko oferty z potwierdzoną dostępnością rozmiaru |
| `--zrodla vinted,olx` | tylko wybrane źródła (`--lista-zrodel` pokazuje wszystkie) |
| `--odswiez` | pomija pamięć podręczną i pobiera wszystko od nowa |
| `--odkrywaj` | szuka nowych sklepów w Google od razu, bez czekania tygodnia |
| `--ukryj "LINK"` | ukrywa ofertę w kolejnych wynikach (można podać kilka linków) |
| `--pokaz-ukryte` | pokazuje także ukryte oferty |
| `--reset-blokad` | zdejmuje wstrzymania hostów po wykryciu ochrony antybotowej |
| `--widoczna-przegladarka` | pokazuje okna przeglądarki używanej dla OLX i Goalinn |
| `--nie-otwieraj` | nie otwiera raportu HTML |
| `-v` | więcej szczegółów w trakcie działania |

## Katalog modeli

Każda marka ma plik w `katalog/` (np. `katalog/joma.toml`), a `katalog/wspolne.toml` trzyma ustawienia wspólne dla wszystkich: listę rozmiarów, numery rozmiarów na Vinted, kategorie eBaya i sklepy, które szukają po frazie (Sportano, Revealsport, Gain Control).

Profil wyszukiwania składa się z trzech poziomów, od ogólnego do szczegółowego: wspólne, marka, model. Zasady łączenia:

* `wykluczenia`, `kody_wykluczone` i `nie_dotyczy` sumują się (np. Joma wyklucza turfy dla każdego modelu, a Top Flex dodatkowo Rebound)
* sekcje takie jak `[vinted]` czy `[olx]` łączą się pole po polu
* `[[sklep]]` sumują się, a sklep o tej samej nazwie na niższym poziomie zastępuje wyższy
* pozostałe pola z niższego poziomu zastępują wyższe
* `inne_modele_marki` program układa sam z pozostałych modeli marki i listy `inne_modele` z pliku marki

Plik marki ma pola profilu (bez `model`) i listę modeli `[[model]]`. Każdy model ma `id` (używane w `--model` i w nazwie katalogu z danymi), `model` (słowa, które muszą być w tytule) i opcjonalnie `nazwa` oraz dowolne pola profilu. Sekcje modelu zapisuje się jako `[model.olx]`, `[[model.sklep]]` itd. Bez `frazy` program użyje „marka model” i „halowki marka model”.

Nike i Adidas robią te same modele na różne nawierzchnie, dlatego ich pliki mają `oznaczenia_hali`: wzorce typu `\bic\b`, `\bin\b`, „halówki”, „futsal”. Oferta z nazwą modelu, ale bez takiego oznaczenia trafia do sprawdzenia zamiast na listę pewnych. Modele halowe z natury (Gato, Top Sala, Super Sala) mają `oznaczenia_hali = []`.

Reguły dla modeli spoza Munich Continental i Joma Top Flex są na razie proste: nazwa, wykluczenia nawierzchni i lista innych modeli marki. Kody produktów warto dopisywać dopiero po sprawdzeniu ich na prawdziwych ofertach.

## Własny profil

Model spoza katalogu można opisać w osobnym pliku i uruchomić przez `--profil plik.toml`. Minimalny profil wystarczy do działania:

```toml
marka = "Joma"
model = "Top Flex"
rozmiar = "42"
wykluczenia = ['rebound', '\bjr\b', 'junior']
```

Wtedy program sam układa frazy wyszukiwania („joma top flex”), sam znajduje markę na Vinted i używa domyślnych linków ręcznych. Każda dodatkowa informacja poprawia trafność.

| Pole | Znaczenie |
|---|---|
| `nazwa` | nazwa w raporcie (domyślnie marka + model) |
| `marka`, `model` | **wymagane**; oferta musi zawierać markę i wszystkie słowa modelu |
| `rozmiar` | rozmiar EU |
| `aliasy_marki` | inne zapisy marki, np. `["munchen"]` dla Munich |
| `frazy` | frazy wyszukiwania; pierwsza jest główna |
| `opis_wykluczen` | krótki opis do raportu, np. „bez V2 i Premium” |
| `wykluczenia` | wzorce wersji, których nie chcesz (np. `'\bv\s?2\b'`, `'rebound'`) |
| `kody_modelu` | wzorce kodów produktu szukanego modelu; kod rozstrzyga nawet bez nazwy |
| `kody_wykluczone` | wzorce kodów innych wersji |
| `inne_modele_marki` | nazwy innych modeli marki; ogłoszenie z taką nazwą jest odrzucane |
| `nie_dotyczy` | słowa oznaczające zupełnie inne produkty (np. opony Continental) |
| `oznaczenia_hali` | wzorce oznaczenia wersji halowej (np. `'\bic\b'`); bez nich oferta z nazwą modelu idzie do sprawdzenia |
| `slowa_kategorii` | słowa typu „halówki”, „futsal”; ogłoszenie bez nazwy modelu trafia do sekcji „do sprawdzenia” tylko z takim słowem |
| `[[wskazowki]]` | wskazówki z opisu ogłoszenia: `wzorzec`, opcjonalnie `oprocz`, `werdykt` (`odrzuc` albo `sprawdz`), `opis` |
| `wskazowka_zdjec` | podpowiedź w raporcie, jak odróżnić model na zdjęciu |
| `[vinted]` | `marka_id` (jeśli puste, program sam je znajdzie), `katalog_obuwia`, `rozmiary` (np. `{ "41" = 782 }`) |
| `[olx]` | `zapytania`: lista par `["fraza-w-adresie", liczba_stron]` |
| `[allegro_lokalnie]`, `[ceneo]` | własne `frazy` dla tych serwisów |
| `[ebay]` | `zapytanie`, `kategorie` (domyślnie obuwie sportowe i halowe) |
| `[futbolemotion]`, `[rgol]` | `zapytanie` w wyszukiwarce sklepu |
| `[goalinn]` | `lista`: adres listy produktów w Goalinnie; bez niego Goalinn jest pomijany |
| `[odkrywanie]` | `frazy` dla Google: `["fraza {rozmiar}", "kraj", "język"]` |
| `[minimalne_odczyty]` | minimalna liczba odczytanych pozycji na źródło (do wykrywania awarii) |
| `[[sklep]]` | sklep: `nazwa`, `lista` (adres listy lub wyszukiwarki), `wzor_linku` (wzorzec adresu produktu), opcjonalnie `wysylka`, `max_produktow`, `dostawa_szacunkowa`, `uwagi` |
| `[[reczny]]` | link do ręcznego sprawdzenia: `nazwa`, `url`, `opis`, opcjonalnie `bez_klucza = "ebay"` |

W adresach i frazach można używać zmiennych `{fraza}`, `{fraza_url}`, `{fraza_z_rozmiarem_url}`, `{rozmiar}`, `{marka}` i `{model}`.

Wzorce to wyrażenia regularne zapisane w apostrofach (`'...'`), sprawdzane na tekście małymi literami bez polskich znaków („halówki” jest porównywane jako „halowki”).

**Jakość wyników zależy od profilu.** Dla Munich Continental profil zna kody produktu i odróżnia klasyka od V2. Dla nowego modelu warto dopisać wykluczenia podobnych wersji (dziecięcych, turfów, wersji „Pro” itp.), bo inaczej trafią na listę.

Każdy model ma osobną historię cen, odkryte sklepy i statystyki źródeł (`dane/profile/<marka>-<model>/`) oraz osobny raport dla każdego rozmiaru (`wyniki/<marka>-<model>/<rozmiar>/`). Pamięć podręczna stron i limity zapytań są wspólne, więc dwa profile nie podwajają ruchu do tych samych stron.

## Interfejs w przeglądarce (Szatnia)

Szatnia prowadzi przez cztery kroki: marka, model, rozmiar (można kilka) i filtry (cena z progami 200, 300, 400 i 500 zł, tylko potwierdzony rozmiar, świeże dane, wybór źródeł). Podczas przewijania na dole ekranu jest przypięty pasek z podsumowaniem i przyciskiem „Szukaj ofert” (skrót Ctrl ↵, na Macu ⌘ ↵). Na końcu filtrów pasek płynnie wsiada w stronę jako jej zwykły element, a po przewinięciu w górę wraca na dół ekranu. Wybór zostaje w przeglądarce po odświeżeniu strony.

Kilka rozmiarów naraz to kolejne przejścia tego samego wyszukiwania. Większość stron z pierwszego przejścia jest już w pamięci podręcznej, więc drugi rozmiar idzie kilka razy szybciej (w teście: 42 w 35 s, 43 w 10 s).

W trakcie szukania widać pasek postępu, stan każdego źródła i oferty, które spływają od razu, gdy źródło skończy. W scenie 3D każde źródło to świecąca kula na orbicie wokół buta: pulsuje, gdy trwa sprawdzanie, a potem zmienia kolor (zielony gotowe, żółty wstrzymane lub podejrzane, czerwony błąd). „Przerwij szukanie” (albo Esc) zatrzymuje wszystko w około sekundę, także w trakcie odstępów między zapytaniami. Wyniki ze źródeł, które zdążyły, zostają zapisane.

Wyniki są w trzech grupach (potwierdzony rozmiar, rozmiar do sprawdzenia, model do sprawdzenia na zdjęciu), z zakładką dla każdego rozmiaru, filtrem źródła, sortowaniem i stronicowaniem po 12. Nad listą jest blok „Od ostatniego sprawdzenia” (nowe, tańsze, droższe, które zniknęły), a karty mają znaczki „nowa” i „taniej o X zł”. Przycisk „Ukryj” chowa ofertę od razu i zapisuje ją w `ukryte.txt`, a powiadomienie pozwala to cofnąć. Na końcu są linki do stron, które trzeba sprawdzić ręcznie.

Własne modele dodaje tylko administrator. Najpierw ustaw hasło (zapisuje się jako skrót argon2 w `.env`):

```bash
py serwer.py --ustaw-haslo
```

Potem zaloguj się na stronie `/admin.html`. Po zalogowaniu w kroku „Model” pojawi się przycisk „Dodaj własny model”. Logowanie ma limit 5 prób na 15 minut, a sesja trwa 12 godzin (ciasteczko HttpOnly, SameSite=Strict). Bez zalogowania serwer odrzuca dodawanie i usuwanie modeli.

Własny model spoza katalogu dodasz przyciskiem „Dodaj własny model” w kroku „Model”. Podajesz markę (także nową), nazwę modelu i słowa do pominięcia, np. rebound albo jr, z gotowymi podpowiedziami. Model od razu trafia do katalogu i można go wyszukać. Własne modele są w `dane/wlasne_modele.json`, a usuwa się je w tym samym oknie, z potwierdzeniem.

Wybór jest zapisany w adresie strony, np. `?marka=nike&model=tiempo&rozmiar=43,44`, więc link otwiera od razu ten model i rozmiary.

**Najprościej (jeden serwer):** zbuduj interfejs raz, a potem uruchamiaj tylko serwer. Strona będzie pod `http://127.0.0.1:8765`.

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

**Przy pracy nad interfejsem** (podgląd zmian na żywo) wymagany jest Node.js 20 lub nowszy. Najpierw uruchom serwer API, a potem w drugim terminalu:

```bash
cd interfejs
```

```bash
npm install
```

```bash
npm run dev
```

Interfejs działa pod `http://127.0.0.1:5190` i przekazuje zapytania `/api` do serwera na porcie 8765. Testy end-to-end (komputer i telefon, same uruchamiają oba serwery, wyszukiwanie jest udawane, więc nie odpytują sklepów):

```bash
npm run test:e2e
```

Obok kroków stoi scena 3D (Three.js): stylizowany but zbudowany w kodzie, bez cudzych modeli i logo. Kolory zmieniają się pod wybraną markę, but podskakuje przy zmianie marki, a kamera przesuwa się z każdym krokiem. W kroku „Rozmiar” kamera patrzy z góry na miarkę 38–46, a nosek buta pokazuje największy zaznaczony rozmiar. Scena ładuje się osobno, już po wyświetleniu strony. Przy ustawieniu „ogranicz ruch” w systemie i w przeglądarkach bez WebGL zostaje płaski rysunek buta.

### Prawdziwy model 3D buta

Scena pokazuje prawdziwe modele: na starcie losowy, po wyborze marki losowy z tej marki, a po wyborze linii jej własny model. But stylizowany zostaje tylko wtedy, gdy nie ma żadnego pliku GLB (np. w świeżej kopii repozytorium).

Zamiast stylizowanego buta scena może pokazać prawdziwy model. Wystarczy plik `interfejs/public/modele/<marka>-<model>.glb`, np. `munich-continental.glb`. Te pliki są w `.gitignore`, bo powstają z prywatnych zdjęć. Serwer sam go wykryje, a scena wczyta go po wybraniu tego modelu. Program sam ustawia but: obraca go wzdłuż, skaluje do długości rozmiaru 42, stawia na podłodze i odwraca, jeśli pięta wypadła z przodu. Modele bez pliku i uszkodzone pliki dostają but stylizowany.

Model powstaje z Twoich zdjęć (generator AI). Jak je zrobić:

1. Jeden but, czysty, sznurówki zawiązane równo.
2. Gładkie, kontrastowe tło (jasne dla ciemnego buta, ciemne dla jasnego), światło dzienne, bez lampy błyskowej i ostrych cieni.
3. Cztery zdjęcia z wysokości buta, z tej samej odległości: bok zewnętrzny, bok wewnętrzny, przód (nosek) i tył (pięta).
4. Cały but w kadrze, zajmuje ok. 70% zdjęcia, ostry, bez rąk i innych przedmiotów.
5. Zdjęcia w pełnej rozdzielczości (JPG lub PNG) w katalogu `models/<marka>/<model>/`, np. `models/munich/continental/` albo `models/nike/phantom/`. Katalogi dla wszystkich modeli z katalogu już są. Cały `models/` jest w `.gitignore`.

### Generowanie modeli 3D ze zdjęć

Narzędzie `narzedzia/modele3d/generuj.py` wysyła wybrane zdjęcia każdego modelu (lista w `wybor_zdjec.json`, tylko ujęcia jednego buta, bez par i zdjęć na nodze) do generatora TRELLIS na Hugging Face. Usuwa tło, które generator odtwarza pod butem jako „podłogę”, kompresuje plik (meshopt i tekstury WebP, ok. 130–280 KB) i zapisuje go w `interfejs/public/modele/`. Gotowe modele pomija, więc można je uruchamiać codziennie, aż będą wszystkie.

Token Hugging Face (typ Read, z huggingface.co/settings/tokens) wpisz do `.env` jako `HF_TOKEN=...`. Darmowe konto pozwala na ok. 5 modeli dziennie, a konto PRO na ok. 25 minut GPU dziennie.

```bash
python3.12 -m venv narzedzia/modele3d/.venv
```

```bash
narzedzia/modele3d/.venv/bin/pip install -r narzedzia/modele3d/requirements.txt
```

```bash
narzedzia/modele3d/.venv/bin/python narzedzia/modele3d/generuj.py
```

Pojedynczy model: `generuj.py nike/gato`. Ponowne wygenerowanie istniejącego: `--od-nowa`. Lista brakujących: `--brakujace`.

Na tym komputerze działa codzienne zadanie macOS `pl.szatnia.modele3d` (`~/Library/LaunchAgents/pl.szatnia.modele3d.plist`). Codziennie o 2:00 (albo po wybudzeniu komputera) uruchamia `narzedzia/modele3d/codziennie.sh`, a ten generuje brakujące modele, aż skończy się dzienny limit. Po zrobieniu ostatniego modelu zadanie samo się usuwa. Przebieg zapisuje się w `narzedzia/modele3d/generuj.log`. Żeby wyłączyć je wcześniej:

```bash
launchctl bootout gui/$(id -u)/pl.szatnia.modele3d
```

```bash
rm ~/Library/LaunchAgents/pl.szatnia.modele3d.plist
```

## Serwer API (dla interfejsu w przeglądarce)

```bash
py serwer.py
```

Serwer działa tylko lokalnie pod `http://127.0.0.1:8765`. Opis wszystkich adresów z możliwością wypróbowania jest pod `/api/dokumentacja`.

| Metoda i adres | Działanie |
|---|---|
| `GET /api/zdrowie` | czy serwer działa i id trwającego wyszukiwania |
| `GET /api/katalog` | rozmiary, marki i modele z katalogu |
| `GET /api/katalog/{marka}/{model}/zrodla` | źródła dla modelu i to, czy są dostępne (np. eBay bez klucza nie jest) |
| `GET /api/katalog/{marka}/{model}/wyniki/{rozmiar}` | ostatnie zapisane wyniki (`oferty.json`) |
| `POST /api/wyszukiwania` | start wyszukiwania; odpowiada `202` z `id`, a `409`, gdy trwa inne |
| `GET /api/wyszukiwania/{id}` | stan i gotowe wyniki dla każdego rozmiaru |
| `GET /api/wyszukiwania/{id}/zdarzenia` | postęp na żywo (Server-Sent Events) |
| `POST /api/wyszukiwania/{id}/przerwij` | przerywa wyszukiwanie; bieżący rozmiar kończy się wynikami częściowymi, kolejne są pomijane |
| `POST /api/ukryte` | ukrywa ofertę, body `{"url": "..."}` |
| `POST /api/ukryte/przywroc` | cofa ukrycie oferty, body `{"url": "..."}` |
| `GET /api/admin` | czy przeglądarka jest zalogowana jako administrator |
| `POST /api/admin/logowanie` | logowanie administratora, body `{"haslo": "..."}` |
| `POST /api/admin/wylogowanie` | wylogowanie |
| `GET /api/wlasne` | lista własnych modeli |
| `POST /api/wlasne` | dodaje własny model (tylko administrator), body `{"marka", "model", "wykluczenia", "opis", "wymagaj_oznaczenia_hali"}` |
| `DELETE /api/wlasne/{marka}/{model}` | usuwa własny model (tylko administrator) |

Przykład startu wyszukiwania dwóch rozmiarów w dwóch źródłach:

```bash
curl -X POST http://127.0.0.1:8765/api/wyszukiwania -H "Content-Type: application/json" -d "{\"marka\": \"nike\", \"model\": \"tiempo\", \"rozmiary\": [\"42\", \"43\"], \"zrodla\": [\"vinted\", \"r-gol\"]}"
```

Pola: `marka`, `model`, `rozmiary` (38–46, do 9 naraz) oraz opcjonalnie `zrodla`, `max_cena`, `tylko_pewne`, `odswiez`, `reset_blokad`, `pokaz_ukryte`. Inne pola są odrzucane. Naraz trwa tylko jedno wyszukiwanie, bo wszystkie korzystają z tych samych limitów zapytań do stron.

Zdarzenia w strumieniu mają kolejne `id`, więc po zerwaniu połączenia przeglądarka wznawia od miejsca przerwania (nagłówek `Last-Event-ID` albo `?od=`). Typy zdarzeń:

| Typ | Kiedy | Najważniejsze dane |
|---|---|---|
| `wyszukiwanie_start` | na początku | `rozmiary` |
| `start` | start rozmiaru | `rozmiar`, `zrodla`, `wstrzymane_hosty` |
| `zrodlo_start` | źródło zaczyna | `zrodlo` |
| `log` | komunikat źródła | `zrodlo`, `tekst` |
| `zrodlo_koniec` | źródło skończyło | `status`, `ofert`, `odczytano`, `oferty` (już z ceną w zł) |
| `koniec` | rozmiar gotowy | `wyniki` w formacie `oferty.json` |
| `blad` | wyszukiwanie przerwane błędem | `komunikat` |
| `przerywanie` | po prośbie o przerwanie | brak |
| `wyszukiwanie_koniec` | zawsze na końcu | `stan` (`gotowe`, `przerwane` albo `blad`) |

Serwer przyjmuje tylko adresy `localhost` i `127.0.0.1` (ochrona przed DNS rebinding), odrzuca żądania wysłane z obcych stron (nagłówek `Origin`) i dodaje nagłówki bezpieczeństwa, w tym Content-Security-Policy. Jeśli istnieje `interfejs/dist`, serwer podaje też stronę, a nieznane adresy dostają własną stronę 404.

Strona ma politykę prywatności i regulamin (`interfejs/polityka-prywatnosci.html`, `interfejs/regulamin.html`), favicon, obraz Open Graph 1200x630 (`interfejs/public/og.png`), `robots.txt` i `sitemap.xml`. Pola `[[...]]` (dane administratora, domena) trzeba uzupełnić przed udostępnieniem strony innym osobom.

## Testy

Sprawdzają, że każdy model z katalogu składa się w poprawny profil w każdym rozmiarze, że reguły rozpoznają typowe tytuły ofert, oraz całe API ze strumieniem zdarzeń na udawanym silniku (bez łączenia z internetem):

```bash
py -m unittest discover -s testy -t .
```

## Źródła

| Źródło | Sposób | Rozmiar |
|---|---|---|
| Vinted (wysyłka przez Vinted) | strona katalogu, filtr marki | z pola „Rozmiar” |
| OLX | prawdziwa przeglądarka Chrome (Playwright) | z tytułu, a gdy go brak, z opisu ogłoszenia |
| Ceneo (porównywarka polskich sklepów) | strony produktów | rozmiar i cena przy ofertach sklepów |
| Goalinn / Tradeinn (Hiszpania, wysyła do PL) | prawdziwa przeglądarka Chrome, wybiera rozmiar i odczytuje jego cenę | lista dostępnych rozmiarów |
| R-GOL | API wyszukiwarki sklepu (Luigi's Box) | lista dostępnych rozmiarów |
| Fútbol Emotion (Hiszpania, wysyła do PL) | API wyszukiwarki sklepu | lista dostępnych rozmiarów |
| Sklepy z profilu (np. Sportano, Revealsport, Redbox, oficjalny sklep marki) | strony produktów | dostępność rozmiaru z wariantów produktu |
| Allegro Lokalnie | strona wyników | z tytułu lub opisu |
| eBay (DE, ES, IT, FR, GB) | oficjalne API, tylko kategorie obuwia, tylko z wysyłką do PL | z tytułu lub parametrów aukcji |
| Odkrywanie (Google przez SerpAPI) | raz w tygodniu frazy w kilku językach; znalezione strony produktów są sprawdzane codziennie | dostępność rozmiaru z danych produktu |

Allegro, Decathlon, Zalando, Amazon (i eBay bez klucza API) blokują automaty (DataDome, Cloudflare, Akamai). Program ich nie obchodzi: w raporcie są gotowe linki do ręcznego sprawdzenia, posortowane od najtańszych tam, gdzie się da.

W Goalinnie cena zależy od rozmiaru i zmienia się nawet kilka razy dziennie, więc może się różnić o kilka złotych od tej w raporcie. Goalinn i OLX działają przez prawdziwą przeglądarkę i każde z nich ma osobny profil Chrome w `dane/profil_przegladarki`.

Parser stron produktów czyta dane strukturalne sklepów (JSON-LD, także rozbite na fragmenty i osobne dla każdego rozmiaru) oraz typowe układy wyboru rozmiaru: PrestaShop (listy i przyciski), Magento, WooCommerce i przyciski rozmiarów z oznaczeniem niedostępności.

## Jak program chroni Twoje IP przed blokadą

* **Jedno zapytanie naraz do danej strony.** Różne sklepy są sprawdzane równolegle, ale do jednego hosta zapytania idą po kolei.
* **Odstępy z losowym rozrzutem.** Domyślnie 7–12 s między zapytaniami do tego samego hosta, dla OLX 11–19 s, dla Vinted 9–15 s. Ustawienia są w `szukacz/ustawienia.py` (`LIMITY`).
* **Limit zapytań na uruchomienie.** Każdy host ma maksymalną liczbę zapytań na jedno uruchomienie (np. Vinted 16, OLX 18, Goalinn 22), więc program nie „przeczesuje” stron bez końca.
* **Pamięć podręczna na 6 godzin.** Ponowne uruchomienie nie pobiera tych samych stron, tylko korzysta z kopii w `dane/cache`.
* **Odstępy pamiętane między uruchomieniami.** Czas ostatniego zapytania do hosta jest zapisywany w `dane/stan_hostow.json`, więc szybkie ponowne uruchomienie też odczeka.
* **Reakcja na sygnały serwera.** Przy HTTP 429/503 program respektuje nagłówek `Retry-After` i zwalnia. Przy wykryciu ochrony antybotowej (captcha, 403) przestaje odpytywać ten host na 12 godzin, zamiast próbować dalej. Odrzucenie klucza przez API (np. eBay) nie jest traktowane jak blokada.
* **Spójna tożsamość.** Jedna sesja z ciasteczkami na host i stały zestaw nagłówków przeglądarki.

## Co pokazuje raport

Na górze jest blok **„Od ostatniego sprawdzenia”**: nowe oferty, tańsze, droższe i te, które zniknęły. Znikające oferty są liczone tylko ze źródeł, które tym razem zadziałały poprawnie, więc awaria strony nie wygląda jak wyprzedanie butów.

Dalej oferty są podzielone na trzy grupy:

1. **Potwierdzony rozmiar**: model na pewno się zgadza, a sklep lub ogłoszenie potwierdza rozmiar.
2. **Rozmiar do sprawdzenia**: model się zgadza, ale strona nie podaje rozmiaru jednoznacznie.
3. **Marka w danym rozmiarze, model do sprawdzenia na zdjęciu**: używane buty tej marki bez nazwy modelu w tytule (np. „halówki Munich 41”). Zdjęcia w raporcie HTML są tu większe.

## Jak program rozpoznaje model

Kolejność sprawdzania, od najpewniejszego:

1. **Wykluczenia z profilu:** oferta z nazwą wykluczonej wersji jest odrzucana.
2. **Kody produktu:** kod innej wersji odrzuca ofertę, a kod szukanego modelu ją potwierdza.
3. **Nazwa modelu:** wszystkie słowa modelu muszą być w tytule.
4. **Inne modele marki:** nazwa innego modelu odrzuca ofertę.
5. **Opis ogłoszenia** (Vinted, OLX, Allegro Lokalnie), gdy tytuł nie podaje modelu: ten sam zestaw reguł plus wskazówki z profilu.

Przykład z profilu Munich Continental:

| Sygnał | Continental (klasyk) | V2 |
|---|---|---|
| Kod produktu | 4100xxx, np. 4100944, 4100958 | 4104xxx, 4770xxx |
| Nazwa | „Continental” + 3-cyfrowy kolor, np. 944, 973 | „V2”, „V 2”, „Continental II” |
| Materiał w opisie (tylko wskazówka) | skóra, zamsz, skóra kangura | syntetyk, mikrofibra, poliester |

## Ukrywanie ofert

* **W raporcie HTML** przycisk „ukryj” chowa ofertę od razu i kopiuje do schowka polecenie, które ukryje ją też w terminalu.
* **W terminalu:**

  ```bash
  py szukaj.py --ukryj "https://link-do-oferty"
  ```

Ukryte linki są w pliku `ukryte.txt` (jeden link w linii), wspólnym dla wszystkich profili. Żeby przywrócić ofertę, usuń jej linię z tego pliku. Plik jest w `.gitignore`.

## Ceny i dostawa

Cena w raporcie to cena z dostawą. Źródło kosztu dostawy, od najpewniejszego:

* **Koszt podany przez sklep** (np. Revealsport 14,99 zł, Sportano z danych produktu).
* **Cennik:** Fútbol Emotion, wysyłka standardowa do PL 35,02 zł.
* **Szacunek oznaczony „~” i „(szac.)”:** Vinted ok. 18 zł, OLX z Przesyłką OLX ok. 15 zł, polskie sklepy ok. 15 zł.

Goalinn i sklepy zagraniczne nie podają kosztu wysyłki do PL, więc ich ceny są bez dostawy. Szacunki dla źródeł stałych są w `szukacz/ustawienia.py` (`WYSYLKA_SZACUNKOWA`; `None` oznacza „nie doliczaj”). Dla sklepów z profilu służy pole `dostawa_szacunkowa`.

Ceny z Vinted zawierają opłatę za ochronę kupującego. W Ceneo program bierze cenę najtańszej oferty, przy której sklep wpisał szukany rozmiar. Jeśli żaden nie wpisał, bierze najniższą cenę produktu i to zaznacza.

## Odkrywanie nowych sklepów (SerpAPI)

Ten moduł szuka w Google sklepów, których program nie zna. Frazy w kilku językach pochodzą z profilu (`[odkrywanie]`), a bez nich program użyje głównej frazy z rozmiarem dla Polski, Niemiec, Hiszpanii, Włoch, Francji i Wielkiej Brytanii. Każdą znalezioną stronę przepuszcza przez ten sam parser co sklepy.

* **Wyszukiwanie** idzie raz w tygodniu na profil (6–7 zapytań). Mieści się to w darmowym planie SerpAPI.
* **Znalezione strony** są zapamiętywane i sprawdzane przy każdym uruchomieniu (do 25 stron).
* **Strony, które nie są produktem**, są pomijane do następnego cotygodniowego wyszukiwania.
* **Co jest pomijane:** serwisy i sklepy obsługiwane osobno, sklepy zbanowane, portale społecznościowe, agregatory oraz domeny spoza UE.
* **Wysyłka:** sklep z domeną .pl ma wysyłkę „tak”. Przy sklepach zagranicznych raport pisze „sprawdź, czy sklep wysyła do PL” i nie dolicza ich kosztu dostawy.

Konfiguracja:

1. Załóż darmowe konto na https://serpapi.com i skopiuj klucz API z zakładki **Api Key**.
2. Wpisz go w `.env`:

   ```
   SERPAPI_KEY=twój-klucz
   ```

Zapytania do SerpAPI nie są zapisywane w pamięci podręcznej, bo adres zapytania zawiera klucz.

## Dlaczego nie ma zagranicznych wersji Vinted

Vinted dzieli kraje na regiony i kupować można tylko w obrębie swojego regionu. Hiszpania jest w regionie zachodnim, Polska w środkowo-wschodnim. Test potwierdził, że to dwa osobne rynki: vinted.es miał 96 ogłoszeń Munich Continental, vinted.pl 21 i żadne się nie pokrywały. Z polskiego konta nie da się kupić bezpośrednio z vinted.es, dlatego program tego źródła nie przeszukuje.

## Zbanowane strony

Oferty z domen wpisanych w `ZBANOWANE_HOSTY` w `szukacz/ustawienia.py` są pomijane we wszystkich profilach, bez względu na źródło (obecnie: taternik-sklep.pl).

## Wykrywanie awarii źródeł

Każde źródło raportuje, ile pozycji w ogóle odczytało ze strony, niezależnie od tego, ile z nich pasuje. Program zapamiętuje te liczby osobno dla każdego profilu i oznacza źródło jako **podejrzane**, gdy:

* odczyta mniej niż minimum z `[minimalne_odczyty]` w profilu, albo
* odczyta mniej niż 30% swojej typowej liczby z poprzednich uruchomień.

Wtedy na górze raportu pojawia się ostrzeżenie. Brak wyników z takiej strony oznacza prawdopodobnie zmianę jej wyglądu, a nie brak butów.

## eBay (opcjonalnie)

1. Załóż darmowe konto na https://developer.ebay.com i utwórz klucz „Production”.
2. W pliku `.env` w głównym katalogu projektu wpisz klucze po znaku `=`, bez cudzysłowów:

   ```
   EBAY_CLIENT_ID=twój-app-id
   EBAY_CLIENT_SECRET=twój-cert-id
   ```

   Plik `.env` jest w `.gitignore`, więc klucze nie trafią do repozytorium. `.env.przyklad` to pusty wzór do repozytorium.

Z trzech identyfikatorów, które pokazuje eBay, potrzebne są dwa: **App ID (Client ID)** jako `EBAY_CLIENT_ID` i **Cert ID (Client Secret)** jako `EBAY_CLIENT_SECRET`. Dev ID nie jest używany.

Jeśli program zgłasza `invalid_client`, klucz Production jest najpewniej nieaktywny. eBay wyłącza nowe klucze Production, dopóki aplikacja nie spełni wymogu „Marketplace Account Deletion”:

1. Wejdź na developer.ebay.com, potem **Application Keys**.
2. Przy kluczu Production kliknij link **Marketplace Account Deletion**.
3. Włącz przełącznik **Exempted from Marketplace Account Deletion**, wybierz powód „I do not persist eBay data” i zatwierdź. Pól na adres powiadomień, e-mail i token nie wypełniaj.

Program nie zapisuje odpowiedzi API eBaya na dysku, więc ta deklaracja jest zgodna z prawdą.
