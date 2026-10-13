import csv
import html
import json
import os
import sys
import time

KOLORY = os.environ.get("NO_COLOR") is None and sys.stdout.isatty()


def _k(kod, tekst):
    return f"\033[{kod}m{tekst}\033[0m" if KOLORY else tekst


def zl(x):
    return f"{x:,.2f}".replace(",", " ").replace(".", ",") + " zł"


def _skroc(tekst, n):
    return tekst if len(tekst) <= n else tekst[: n - 1] + "…"


def grupa(o):
    if o.model == "do weryfikacji":
        return "weryfikacja"
    return "pewne" if o.rozmiar_pewny else "rozmiar"


def _opis_dostawy(o):
    if o.dostawa_pln is None:
        return ""
    return f"w tym dostawa {'~' if o.dostawa_szac else ''}{zl(o.dostawa_pln)}{' (szac.)' if o.dostawa_szac else ''}"


def _drukuj_oferte(i, o):
    flagi = "  " + _k("32;1", " ".join(o.flagi)) if o.flagi else ""
    print(f"{i:>3}. {_k('1', f'{zl(o.suma_pln):>12}')}  {_skroc(o.zrodlo, 18):<18} {_skroc(o.stan, 14):<14} {_skroc(o.tytul, 72)}{flagi}")
    print(f"     {_k('36', o.url)}")
    szczegoly = []
    if o.waluta != "PLN":
        szczegoly.append(f"{o.cena:.2f} {o.waluta}")
    for wartosc in (_opis_dostawy(o), o.wysylka and f"wysyłka: {o.wysylka}", o.lokalizacja, o.wskazowka, o.uwagi):
        if wartosc:
            szczegoly.append(wartosc)
    if szczegoly:
        print(f"     {_k('90', ' · '.join(szczegoly))}")


def _drukuj_zmiany(zmiany):
    if zmiany.pierwsze:
        print(_k("1", "Pierwsze uruchomienie: od następnego razu zobaczysz tu, co się zmieniło."))
        return
    kiedy = f" ({zmiany.poprzednio})" if zmiany.poprzednio else ""
    print(_k("1;36", f"═══ Od ostatniego sprawdzenia{kiedy} ═══"))
    if zmiany.puste:
        print("     bez zmian")
        return
    for o in zmiany.nowe:
        print(f"   {_k('32;1', '+ nowa ')}  {zl(o.suma_pln):>12}  {_skroc(o.zrodlo, 16):<16} {_skroc(o.tytul, 60)}")
    for o, roznica in zmiany.tansze:
        print(f"   {_k('32', '↓ taniej')} {zl(o.suma_pln):>12}  {_skroc(o.zrodlo, 16):<16} {_skroc(o.tytul, 60)}  (−{zl(roznica)})")
    for o, roznica in zmiany.drozsze:
        print(f"   {_k('33', '↑ drożej')} {zl(o.suma_pln):>12}  {_skroc(o.zrodlo, 16):<16} {_skroc(o.tytul, 60)}  (+{zl(roznica)})")
    for z in zmiany.zniknely:
        cena = zl(z["cena"]) if z.get("cena") else ""
        print(f"   {_k('90', '− znikła')} {cena:>12}  {_skroc(z['zrodlo'], 16):<16} {_skroc(z['tytul'], 60)}")


def drukuj(profil, oferty, zmiany, wyniki_zrodel, reczne, rozmiar, kursy_przyblizone, ukryto):
    problemy = [w for w in wyniki_zrodel if w.status in ("podejrzane", "błąd")]
    print()
    if problemy:
        print(_k("1;35", f"!!! Uwaga: {len(problemy)} źródeł mogło przestać działać: {', '.join(w.nazwa for w in problemy)}"))
        print(_k("35", "    Brak wyników z tych stron nie oznacza braku butów. Szczegóły na dole listy."))
        print()
    _drukuj_zmiany(zmiany)
    sekcje = [
        ("pewne", "1;32", f"{profil.nazwa}, rozmiar {rozmiar}: potwierdzona dostępność", f"brak ofert z potwierdzonym rozmiarem {rozmiar}"),
        ("rozmiar", "1;33", f"{profil.model}, rozmiar do sprawdzenia w ogłoszeniu", None),
        ("weryfikacja", "1;34", f"{profil.marka} w rozmiarze {rozmiar}, model do sprawdzenia na zdjęciu (może być {profil.model})", None),
    ]
    for klucz, kolor, tytul, pusto in sekcje:
        lista = [o for o in oferty if grupa(o) == klucz]
        if not lista and not pusto:
            continue
        print()
        print(_k(kolor, f"═══ {tytul} ({len(lista)}) ═══"))
        if not lista:
            print(f"     {pusto}")
        for i, o in enumerate(lista, 1):
            _drukuj_oferte(i, o)
    if ukryto:
        print()
        print(_k("90", f"Ukryto {ukryto} ofert z pliku ukryte.txt (pokaż je opcją --pokaz-ukryte)."))
    print()
    print(_k("1", "Źródła:"))
    for w in sorted(wyniki_zrodel, key=lambda w: w.nazwa.lower()):
        kolor = {"ok": "32", "wstrzymane": "33", "podejrzane": "35"}.get(w.status, "31")
        opis = f"{len(w.oferty)} ofert z {w.surowe} odczytanych, {w.zapytania} zapytań, {w.czas:.0f} s"
        print(f"   {_k(kolor, f'{w.status:<11}')} {w.nazwa:<20} {opis}" + (f"  {_k('90', w.komunikat)}" if w.komunikat else ""))
    if reczne:
        print()
        print(_k("1", "Sprawdź ręcznie (strony blokujące automaty):"))
        for nazwa, url, opis in reczne:
            print(f"   {nazwa:<14} {_k('36', url)}")
            print(f"   {'':<14} {_k('90', opis)}")
    if kursy_przyblizone:
        print()
        print(_k("33", f"Uwaga: kursy {', '.join(sorted(kursy_przyblizone))} są przybliżone (brak połączenia z NBP)."))


def zapisz_csv(oferty, plik):
    with open(plik, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["suma_pln", "cena", "waluta", "dostawa_pln", "dostawa_szacunkowa", "rozmiar_potwierdzony", "model", "zrodlo", "tytul", "stan", "wysylka", "lokalizacja", "uwagi", "flagi", "url"])
        for o in oferty:
            w.writerow([
                f"{o.suma_pln:.2f}".replace(".", ","),
                f"{o.cena:.2f}".replace(".", ","),
                o.waluta,
                "" if o.dostawa_pln is None else f"{o.dostawa_pln:.2f}".replace(".", ","),
                "tak" if o.dostawa_szac else "",
                "tak" if o.rozmiar_pewny else "do sprawdzenia",
                o.model,
                o.zrodlo, o.tytul, o.stan, o.wysylka, o.lokalizacja, " · ".join(x for x in (o.wskazowka, o.uwagi) if x), " ".join(o.flagi), o.url,
            ])


def zapisz_json(profil, oferty, zmiany, wyniki_zrodel, reczne, rozmiar, plik):
    dane = {
        "wygenerowano": time.strftime("%Y-%m-%d %H:%M"),
        "rozmiar": rozmiar,
        "nazwa": profil.nazwa,
        "marka": profil.marka,
        "model": profil.model,
        "profil": profil.slug,
        "wskazowka_zdjec": profil.wskazowka_zdjec,
        "oferty": [{**o.do_slownika(), "klucz": o.klucz, "grupa": grupa(o)} for o in oferty],
        "zmiany": zmiany.do_slownika(),
        "zrodla": [
            {"nazwa": w.nazwa, "status": w.status, "komunikat": w.komunikat, "ofert": len(w.oferty), "odczytano": w.surowe, "zapytan": w.zapytania}
            for w in wyniki_zrodel
        ],
        "recznie": [{"nazwa": n, "url": u, "opis": o} for n, u, o in reczne],
    }
    plik.write_text(json.dumps(dane, ensure_ascii=False, indent=1), encoding="utf-8")
    return dane


SZABLON = """<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__NAZWA__ __ROZMIAR__</title>
<style>
:root{--tlo:#f6f5f2;--karta:#fff;--tekst:#1c1b19;--szary:#6b6862;--linia:#e4e1da;--akcent:#0d6b4f;--akcent-tlo:#e3f2ec;--ostrz:#9a5b00;--ostrz-tlo:#fbf0dc;--czer:#a3322a;--czer-tlo:#fbe7e5;--nieb:#2b5c9e;--nieb-tlo:#e6eef9}
@media (prefers-color-scheme:dark){:root{--tlo:#141413;--karta:#1d1d1b;--tekst:#ecebe7;--szary:#9c998f;--linia:#2f2e2b;--akcent:#5fd0a6;--akcent-tlo:#16332a;--ostrz:#f0b45a;--ostrz-tlo:#3a2a12;--czer:#f08a80;--czer-tlo:#3b1d1a;--nieb:#8db6f0;--nieb-tlo:#1b2a40}}
*{box-sizing:border-box}
body{margin:0;background:var(--tlo);color:var(--tekst);font:15px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1180px;margin:0 auto;padding:28px 16px 60px}
h1{font-size:26px;margin:0 0 4px}
h2{font-size:17px;margin:30px 0 10px}
h2 small{color:var(--szary);font-weight:400}
.pod{color:var(--szary);margin:0 0 18px}
.alarm{background:var(--czer-tlo);color:var(--czer);border-radius:10px;padding:12px 14px;margin-bottom:14px}
.zmiany{background:var(--karta);border:1px solid var(--linia);border-radius:10px;padding:12px 14px;margin-bottom:14px}
.zmiany ul{margin:6px 0 0;padding-left:18px}
.zmiany li{margin:2px 0}
.panel{display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center;background:var(--karta);border:1px solid var(--linia);border-radius:10px;padding:12px 14px;margin-bottom:6px}
.panel label{display:flex;gap:6px;align-items:center;cursor:pointer}
select,input[type=number]{background:var(--tlo);color:var(--tekst);border:1px solid var(--linia);border-radius:6px;padding:5px 8px;font:inherit}
input[type=number]{width:100px}
.lista{display:flex;flex-direction:column;gap:8px}
.of{display:grid;grid-template-columns:76px 1fr auto;gap:14px;align-items:center;background:var(--karta);border:1px solid var(--linia);border-radius:10px;padding:10px 14px}
.of.ukryta{opacity:.45}
.of img,.of .brak{width:76px;height:76px;object-fit:cover;border-radius:8px;background:var(--linia)}
.weryf .of{grid-template-columns:150px 1fr auto}
.weryf .of img,.weryf .of .brak{width:150px;height:150px}
.tyt{font-weight:600;color:var(--tekst);text-decoration:none}
.tyt:hover{text-decoration:underline}
.meta{color:var(--szary);font-size:13px;margin-top:3px}
.znaczki{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
.zn{font-size:12px;padding:2px 8px;border-radius:99px;background:var(--tlo);border:1px solid var(--linia)}
.zn.ok{background:var(--akcent-tlo);color:var(--akcent);border-color:transparent}
.zn.uw{background:var(--ostrz-tlo);color:var(--ostrz);border-color:transparent}
.zn.nb{background:var(--nieb-tlo);color:var(--nieb);border-color:transparent}
.zn.fl{background:var(--akcent);color:var(--karta);border-color:transparent;font-weight:600}
.cena{text-align:right;white-space:nowrap;display:flex;flex-direction:column;align-items:flex-end;gap:4px}
.cena b{font-size:20px}
.cena div{color:var(--szary);font-size:12px}
.ukryj{font:inherit;font-size:12px;color:var(--szary);background:none;border:1px solid var(--linia);border-radius:6px;padding:2px 8px;cursor:pointer}
.ukryj:hover{color:var(--tekst)}
table{width:100%;border-collapse:collapse;background:var(--karta);border:1px solid var(--linia);border-radius:10px;overflow:hidden}
td,th{text-align:left;padding:8px 12px;border-bottom:1px solid var(--linia);font-size:14px;vertical-align:top}
th{color:var(--szary);font-weight:600}
.st-ok{color:var(--akcent)}.st-wstrzymane{color:var(--ostrz)}.st-błąd,.st-podejrzane{color:var(--czer);font-weight:600}
a{color:var(--akcent)}
.pusto{color:var(--szary);padding:16px;text-align:center;background:var(--karta);border-radius:10px;border:1px dashed var(--linia)}
#komunikat{position:fixed;bottom:16px;left:50%;transform:translateX(-50%);background:var(--tekst);color:var(--tlo);padding:8px 14px;border-radius:8px;font-size:13px;display:none;max-width:calc(100% - 32px)}
@media (max-width:640px){.of,.weryf .of{grid-template-columns:64px 1fr}.of img,.of .brak,.weryf .of img,.weryf .of .brak{width:64px;height:64px}.cena{grid-column:2;align-items:flex-start;text-align:left}td,th{padding:6px 8px}}
</style>
</head>
<body>
<main>
<h1>__NAZWA__, rozmiar __ROZMIAR__</h1>
<p class="pod">Wygenerowano __CZAS__ · ceny w złotych z dostawą, gdy jest znana lub szacowana · <span id="licznik"></span></p>
<div id="alarm"></div>
<div id="zmiany"></div>
<div class="panel">
<label><input type="checkbox" id="pewne"> tylko potwierdzony rozmiar</label>
<label>źródło <select id="zrodlo"><option value="">wszystkie</option></select></label>
<label>maks. cena <input type="number" id="max" min="0" step="10" placeholder="zł"></label>
<label>sortuj <select id="sort"><option value="cena">od najtańszych</option><option value="cena-">od najdroższych</option><option value="zrodlo">wg źródła</option></select></label>
<label><input type="checkbox" id="pokazUkryte"> pokaż ukryte</label>
</div>
<div id="sekcje"></div>
<h2>Sprawdź ręcznie</h2>
<table><tbody id="reczne"></tbody></table>
<h2>Stan źródeł</h2>
<table><thead><tr><th>Źródło</th><th>Status</th><th>Ofert</th><th>Odczytano</th><th>Zapytań</th><th>Uwagi</th></tr></thead><tbody id="zrodla"></tbody></table>
</main>
<div id="komunikat"></div>
<script>
const D=__DANE__;
const $=s=>document.querySelector(s);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const zl=x=>x.toLocaleString("pl-PL",{minimumFractionDigits:2,maximumFractionDigits:2})+" zł";
const KLUCZ="poszukiwacz-ukryte-"+D.profil;
let ukryte=new Set();
try{ukryte=new Set(JSON.parse(localStorage.getItem(KLUCZ)||"[]"))}catch(e){}
const zapiszUkryte=()=>{try{localStorage.setItem(KLUCZ,JSON.stringify([...ukryte]))}catch(e){}};
const poKluczu=Object.fromEntries(D.oferty.map(o=>[o.klucz,o]));
function komunikat(t){const k=$("#komunikat");k.textContent=t;k.style.display="block";clearTimeout(k._t);k._t=setTimeout(()=>k.style.display="none",4000)}
const problemy=D.zrodla.filter(z=>z.status==="podejrzane"||z.status==="błąd");
if(problemy.length)$("#alarm").innerHTML=`<div class="alarm"><b>Uwaga:</b> ${problemy.length} źródeł mogło przestać działać (${problemy.map(z=>esc(z.nazwa)).join(", ")}). Brak wyników z tych stron nie oznacza braku butów. Szczegóły w tabeli „Stan źródeł”.</div>`;
(function(){
  const Z=D.zmiany;
  if(Z.pierwsze){$("#zmiany").innerHTML=`<div class="zmiany">Pierwsze uruchomienie: od następnego razu zobaczysz tu, co się zmieniło.</div>`;return}
  const p=[];
  Z.nowe.forEach(k=>{const o=poKluczu[k];if(o)p.push(`<li><b>nowa</b>: <a href="${esc(o.url)}" target="_blank" rel="noopener">${esc(o.tytul)}</a> · ${esc(o.zrodlo)} · ${zl(o.suma_pln)}</li>`)});
  Z.tansze.forEach(t=>{const o=poKluczu[t.klucz];if(o)p.push(`<li><b>taniej o ${zl(t.roznica)}</b>: <a href="${esc(o.url)}" target="_blank" rel="noopener">${esc(o.tytul)}</a> · ${zl(o.suma_pln)}</li>`)});
  Z.drozsze.forEach(t=>{const o=poKluczu[t.klucz];if(o)p.push(`<li>drożej o ${zl(t.roznica)}: ${esc(o.tytul)} · ${zl(o.suma_pln)}</li>`)});
  Z.zniknely.forEach(z=>p.push(`<li>znikła: ${esc(z.tytul)} · ${esc(z.zrodlo)}${z.cena?" · było "+zl(z.cena):""}</li>`));
  $("#zmiany").innerHTML=`<div class="zmiany"><b>Od ostatniego sprawdzenia</b>${Z.poprzednio?" ("+esc(Z.poprzednio)+")":""}${p.length?`<ul>${p.join("")}</ul>`:": bez zmian"}</div>`;
})();
[...new Set(D.oferty.map(o=>o.zrodlo))].sort().forEach(z=>$("#zrodlo").insertAdjacentHTML("beforeend",`<option>${esc(z)}</option>`));
const SEKCJE=[
  ["pewne",`Potwierdzony rozmiar ${esc(D.rozmiar)}`,"",`Brak ofert z potwierdzonym rozmiarem ${esc(D.rozmiar)}.`],
  ["rozmiar","Rozmiar do sprawdzenia w ogłoszeniu","",""],
  ["weryfikacja",`${esc(D.marka)} w rozmiarze ${esc(D.rozmiar)}, model do sprawdzenia na zdjęciu`,esc(D.wskazowka_zdjec),""]
];
function karta(o){
  const zn=[o.rozmiar_potwierdzony?`<span class="zn ok">rozmiar ${esc(D.rozmiar)} dostępny</span>`:`<span class="zn uw">rozmiar do sprawdzenia</span>`];
  if(o.model==="z opisu")zn.push(`<span class="zn nb">model rozpoznany z opisu</span>`);
  if(o.wskazowka&&o.model!=="pewny")zn.push(`<span class="zn nb">${esc(o.wskazowka)}</span>`);
  if(o.stan)zn.push(`<span class="zn">${esc(o.stan)}</span>`);
  if(o.wysylka)zn.push(`<span class="zn">wysyłka: ${esc(o.wysylka)}</span>`);
  if(o.lokalizacja)zn.push(`<span class="zn">${esc(o.lokalizacja)}</span>`);
  o.flagi.forEach(f=>zn.push(`<span class="zn fl">${esc(f)}</span>`));
  const dost=o.dostawa_pln?`w tym dostawa ${o.dostawa_szacunkowa?"~":""}${zl(o.dostawa_pln)}${o.dostawa_szacunkowa?" (szac.)":""}`:"";
  const dod=[o.waluta!=="PLN"?`${o.cena.toFixed(2)} ${esc(o.waluta)}`:"",dost].filter(Boolean).join(" · ");
  const img=o.zdjecie?`<img src="${esc(o.zdjecie)}" alt="" loading="lazy" referrerpolicy="no-referrer">`:`<div class="brak"></div>`;
  const uk=ukryte.has(o.klucz);
  return `<div class="of${uk?" ukryta":""}">${img}<div><a class="tyt" href="${esc(o.url)}" target="_blank" rel="noopener">${esc(o.tytul)}</a><div class="meta">${esc(o.zrodlo)}${o.uwagi?" · "+esc(o.uwagi):""}</div><div class="znaczki">${zn.join("")}</div></div><div class="cena"><b>${zl(o.suma_pln)}</b><div>${dod}</div><button class="ukryj" data-klucz="${esc(o.klucz)}">${uk?"przywróć":"ukryj"}</button></div></div>`;
}
function rysuj(){
  const pewne=$("#pewne").checked,zr=$("#zrodlo").value,max=parseFloat($("#max").value),s=$("#sort").value,pu=$("#pokazUkryte").checked;
  let L=D.oferty.filter(o=>(!pewne||o.rozmiar_potwierdzony)&&(!zr||o.zrodlo===zr)&&(isNaN(max)||o.suma_pln<=max)&&(pu||!ukryte.has(o.klucz)));
  L.sort((a,b)=>s==="cena-"?b.suma_pln-a.suma_pln:s==="zrodlo"?a.zrodlo.localeCompare(b.zrodlo)||a.suma_pln-b.suma_pln:a.suma_pln-b.suma_pln);
  $("#licznik").textContent=`${L.length} z ${D.oferty.length} ofert${ukryte.size?`, ukryte: ${ukryte.size}`:""}`;
  $("#sekcje").innerHTML=SEKCJE.map(([g,tytul,pod,pusto])=>{
    const S=L.filter(o=>o.grupa===g);
    if(!S.length&&!pusto)return "";
    return `<section class="${g==="weryfikacja"?"weryf":""}"><h2>${tytul} <small>(${S.length})${pod?" · "+pod:""}</small></h2><div class="lista">${S.length?S.map(karta).join(""):`<div class="pusto">${pusto}</div>`}</div></section>`;
  }).join("");
}
document.addEventListener("click",async e=>{
  const b=e.target.closest(".ukryj");if(!b)return;
  const k=b.dataset.klucz;
  if(ukryte.has(k)){ukryte.delete(k);zapiszUkryte();rysuj();komunikat("Przywrócono w raporcie. Jeśli oferta jest w ukryte.txt, usuń tam jej linię.");return}
  ukryte.add(k);zapiszUkryte();rysuj();
  const polecenie=`py szukaj.py --ukryj "${k}"`;
  try{await navigator.clipboard.writeText(polecenie);komunikat("Ukryto w raporcie. Skopiowano polecenie, które ukryje ją też w terminalu: "+polecenie)}
  catch(err){komunikat("Ukryto w raporcie. Aby ukryć też w terminalu: "+polecenie)}
});
["#pewne","#zrodlo","#max","#sort","#pokazUkryte"].forEach(s=>$(s).addEventListener("input",rysuj));
$("#reczne").innerHTML=D.recznie.map(r=>`<tr><td><a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.nazwa)}</a></td><td>${esc(r.opis)}</td></tr>`).join("");
$("#zrodla").innerHTML=D.zrodla.sort((a,b)=>a.nazwa.localeCompare(b.nazwa)).map(z=>`<tr><td>${esc(z.nazwa)}</td><td class="st-${esc(z.status)}">${esc(z.status)}</td><td>${z.ofert}</td><td>${z.odczytano}</td><td>${z.zapytan}</td><td>${esc(z.komunikat)}</td></tr>`).join("");
rysuj();
</script>
</body>
</html>
"""


def zapisz_html(dane, plik):
    tresc = (
        SZABLON.replace("__ROZMIAR__", html.escape(dane["rozmiar"]))
        .replace("__NAZWA__", html.escape(dane["nazwa"]))
        .replace("__CZAS__", html.escape(dane["wygenerowano"]))
        .replace("__DANE__", json.dumps(dane, ensure_ascii=False).replace("</", "<\\/"))
    )
    plik.write_text(tresc, encoding="utf-8")
