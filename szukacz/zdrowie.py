import json
import statistics

HISTORIA = 10


def ocen(wyniki, plik):
    try:
        dane = json.loads(plik.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        dane = {}
    podejrzane = []
    for w in wyniki:
        if w.status != "ok":
            continue
        poprzednie = dane.get(w.nazwa, [])
        typowo = statistics.median(poprzednie) if poprzednie else 0
        if w.min_surowych and w.surowe < w.min_surowych:
            w.status = "podejrzane"
            zwykle = f", zwykle ok. {typowo:.0f}" if typowo else ""
            w.komunikat = f"odczytano tylko {w.surowe} pozycji (minimum {w.min_surowych}{zwykle}); strona mogła zmienić wygląd"
        elif typowo >= 5 and w.surowe < 0.3 * typowo:
            w.status = "podejrzane"
            w.komunikat = f"odczytano {w.surowe} pozycji, zwykle ok. {typowo:.0f}; strona mogła zmienić wygląd"
        if w.status == "podejrzane":
            podejrzane.append(w)
        else:
            dane[w.nazwa] = (poprzednie + [w.surowe])[-HISTORIA:]
    plik.parent.mkdir(parents=True, exist_ok=True)
    plik.write_text(json.dumps(dane, ensure_ascii=False, indent=1), encoding="utf-8")
    return podejrzane
