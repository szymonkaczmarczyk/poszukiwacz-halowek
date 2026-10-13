# Poszukiwacz obuwia

Szuka wybranego modelu butów w podanym rozmiarze w sklepach i na marketplace'ach z wysyłką do Polski. Wyniki sortuje od najtańszych, a ceny w euro przelicza po kursie NBP.

Co i w jakim rozmiarze szukać, opisuje **profil**: plik `.toml` w katalogu `profile/`. W zestawie są dwa:

* `munich-continental.toml`: halówki Munich Continental 41, bez V2 i Premium (profil domyślny)
* `joma-top-flex.toml`: halówki Joma Top Flex 42, bez Rebound i wersji dziecięcej

## Uruchomienie

```bash
py -m pip install -r requirements.txt
```

```bash
py szukaj.py
```

```bash
py szukaj.py --profil profile/joma-top-flex.toml
```

Po zakończeniu w terminalu pojawia się lista z linkami, a w przeglądarce otwiera się raport `wyniki/<profil>/raport.html` z filtrami. Te same dane trafiają też do `oferty.csv` (Excel) i `oferty.json` w tym samym katalogu.

Przydatne opcje:

| Opcja | Działanie |
|---|---|
| `--profil PLIK` | wybór profilu (domyślnie `profile/munich-continental.toml`) |
| `--lista-profili` | pokazuje profile z katalogu `profile/` |
| `--rozmiar 42` | inny rozmiar EU niż w profilu |
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

## Własny profil

Najprościej skopiować `profile/joma-top-flex.toml` i zmienić wartości. Minimalny profil wystarczy do działania:

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

Każdy profil ma osobną historię cen, odkryte sklepy i statystyki źródeł (`dane/profile/<profil>/`) oraz osobny raport (`wyniki/<profil>/`). Pamięć podręczna stron i limity zapytań są wspólne, więc dwa profile nie podwajają ruchu do tych samych stron.

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
