from ..dopasowanie import model_profilu, ocen_pole, ocen_tytul, to_szukany_model
from ..modele import Oferta, kwota
from ..silnik import Zadanie

NAZWA = "Goalinn"
MAX_PRODUKTOW = 20

SKRYPT_LISTY = """
async () => {
  const czekaj = ms => new Promise(r => setTimeout(r, ms));
  await czekaj(2500);
  for (let i = 0; i < 4; i++) {
    const przycisk = [...document.querySelectorAll('button')]
      .find(b => /więcej produktów/i.test(b.innerText) && b.offsetParent);
    if (!przycisk) break;
    przycisk.click();
    await czekaj(2500 + Math.random() * 1500);
  }
  const produkty = {};
  for (const a of document.querySelectorAll('a[href]')) {
    if (!/\\/\\d+\\/p$/.test(a.href)) continue;
    const tekst = a.innerText.replace(/\\s+/g, ' ').trim();
    if (tekst) (produkty[a.href] = produkty[a.href] || []).push(tekst);
  }
  return produkty;
}
"""

SKRYPT_PRODUKTU = """
async (rozmiar) => {
  const czekaj = ms => new Promise(r => setTimeout(r, ms));
  await czekaj(1500);
  const pozycje = [...document.querySelectorAll('#detalle_tallas li')];
  const rozmiary = pozycje.map(li => li.innerText.replace(/\\s+/g, ' ').trim());
  const wybrany = pozycje.find(li => (li.innerText.match(/\\d+(?:[.,]\\d+)?/) || [])[0] === rozmiar);
  let cena = null;
  if (wybrany) {
    wybrany.click();
    await czekaj(2000 + Math.random() * 1000);
    const el = document.querySelector('#js-precio') || document.querySelector('#js-contenedor_precio');
    cena = el ? el.innerText.replace(/\\s+/g, ' ').trim() : null;
  }
  const dostawa = (document.body.innerText.match(/[^\\n]*(Wysyłka natychmiastowa|Otrzymaj między|Wysyłka w ciągu|Dostępne za)[^\\n]*/) || [''])[0];
  const obraz = document.querySelector('meta[property="og:image"]');
  return {
    nazwa: (document.querySelector('h1') || {}).innerText || document.title,
    rozmiary,
    wybrany: wybrany ? wybrany.innerText.trim() : null,
    cena,
    dostawa: dostawa.trim(),
    zdjecie: obraz ? obraz.content : ''
  };
}
"""


def _nazwa_z_kart(teksty):
    pasujace = [t for t in teksty if model_profilu(t)[0] == "model"]
    return max(pasujace or teksty, key=len)


def szukaj(k, oferty):
    przegladarka = k.przegladarka("goalinn")
    try:
        produkty = przegladarka.wykonaj(k.profil.goalinn["lista"], SKRYPT_LISTY) or {}
        k.zlicz(len(produkty))
        kandydaci = []
        for url, teksty in produkty.items():
            nazwa = _nazwa_z_kart(teksty)
            if to_szukany_model(nazwa, k.profil.marka) and ocen_tytul(nazwa.split(" zł")[0], k.rozmiar) != "nie":
                cena_karty = kwota(nazwa.split("zł")[-1]) if "zł" in nazwa else None
                kandydaci.append((cena_karty or 10**6, url, nazwa))
        kandydaci.sort()
        k.log(NAZWA, f"{len(produkty)} produktów na liście, {len(kandydaci)} pasuje do modelu", zawsze=False)
        for _, url, nazwa_karty in kandydaci[:MAX_PRODUKTOW]:
            dane = przegladarka.wykonaj(url, SKRYPT_PRODUKTU, k.rozmiar)
            if not dane or not dane.get("wybrany"):
                continue
            if ocen_pole(dane["wybrany"], k.rozmiar) != "tak":
                continue
            nazwa = (dane.get("nazwa") or nazwa_karty).strip()
            cena = kwota(dane.get("cena"))
            if not cena or not to_szukany_model(nazwa, k.profil.marka):
                continue
            oferty.append(Oferta(
                zrodlo=NAZWA,
                tytul=nazwa,
                url=url,
                cena=cena,
                rozmiar_pewny=True,
                stan="nowe",
                wysylka="tak, do PL (Tradeinn, Hiszpania)",
                zdjecie=dane.get("zdjecie") or "",
                uwagi=dane.get("dostawa") or "",
            ))
    finally:
        przegladarka.zamknij()


ZADANIA = [Zadanie(NAZWA, szukaj, ("www.tradeinn.com",))]


def skonfigurowany(profil):
    return bool(profil.goalinn.get("lista"))
