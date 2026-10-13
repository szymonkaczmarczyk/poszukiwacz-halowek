DOMYSLNE = [
    {"nazwa": "Allegro", "url": "https://allegro.pl/listing?string={fraza_z_rozmiarem_url}&order=p",
     "opis": "chronione przez DataDome, otwórz ręcznie (posortowane od najtańszych)"},
    {"nazwa": "eBay", "url": "https://www.ebay.de/sch/i.html?_nkw={fraza_z_rozmiarem_url}&_sop=15",
     "opis": "dodaj klucz eBay API do .env, a eBay będzie przeszukiwany automatycznie", "bez_klucza": "ebay"},
    {"nazwa": "Zalando", "url": "https://www.zalando.pl/katalog/?q={fraza_url}", "opis": "chronione przez Akamai"},
    {"nazwa": "Google Zakupy", "url": "https://www.google.com/search?tbm=shop&q={fraza_z_rozmiarem_url}",
     "opis": "szeroki przegląd sklepów z całej Europy"},
]


def linki(profil, rozmiar, skonfigurowane_klucze):
    lista = []
    for wpis in profil.reczne or DOMYSLNE:
        if wpis.get("bez_klucza") in skonfigurowane_klucze:
            continue
        lista.append((wpis["nazwa"], profil.podstaw(wpis["url"], rozmiar), wpis.get("opis", "")))
    return lista
