from .dopasowanie import model_profilu, wskazowka_opisu, wyglada_na_kategorie


def klasyfikuj(tytul, opis=""):
    model, powod = model_profilu(tytul)
    if model != "?":
        return model, "pewny", powod
    if opis:
        model, powod = model_profilu(opis)
        if model == "model":
            return "model", "z opisu", f"{powod} w opisie"
        if model != "?":
            return model, "z opisu", powod
        werdykt, powod = wskazowka_opisu(opis)
        if werdykt == "odrzuc":
            return "wykluczony", "z opisu", powod
        if werdykt == "sprawdz":
            return "?", "do weryfikacji", powod
    return "?", "do weryfikacji", "brak nazwy modelu, sprawdź zdjęcie"


def do_listy(tytul, opis=""):
    model, pewnosc, powod = klasyfikuj(tytul, opis)
    if model == "model":
        return pewnosc, powod
    if model == "?" and wyglada_na_kategorie(f"{tytul} {opis}"):
        return pewnosc, powod
    return None, powod


def wymaga_opisu(tytul):
    return model_profilu(tytul)[0] == "?"
