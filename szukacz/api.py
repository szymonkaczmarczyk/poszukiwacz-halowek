import asyncio
import json
import threading
import time
import uuid
from collections import OrderedDict
from urllib.parse import urlsplit
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from . import admin as A
from . import katalog, przebieg, ukryte, wlasne
from . import ustawienia as U

HOSTY = ["127.0.0.1", "localhost"]
PORT = 8765
PORT_INTERFEJSU = 5190
PORT_PODGLADU = 4190
DOZWOLONE_ZRODLA_STRON = {f"http://{h}:{p}" for h in HOSTY for p in (PORT, PORT_INTERFEJSU, PORT_PODGLADU)}
PING_CO_SEKUND = 15
PAMIETANE_WYSZUKIWANIA = 10

NAGLOWKI_BEZPIECZENSTWA = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' https: data: blob:; script-src 'self' 'wasm-unsafe-eval'; style-src 'self'; "
        "font-src 'self'; connect-src 'self' blob:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
    ),
}


class Zapytanie(BaseModel):
    model_config = ConfigDict(extra="forbid")

    marka: str = Field(min_length=1, max_length=40)
    model: str = Field(min_length=1, max_length=60)
    rozmiary: list[str] = Field(min_length=1, max_length=9)
    zrodla: list[str] = Field(default_factory=list, max_length=40)
    max_cena: float | None = Field(default=None, gt=0, le=100000)
    tylko_pewne: bool = False
    odswiez: bool = False
    reset_blokad: bool = False
    pokaz_ukryte: bool = False


WZOR_NAZWY = r"^[\w][\w .+/-]*$"
WZOR_SLOWA = r"^[\w][\w .-]*$"


class NowyModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    marka: str = Field(min_length=2, max_length=40, pattern=WZOR_NAZWY)
    model: str = Field(min_length=2, max_length=40, pattern=WZOR_NAZWY)
    wykluczenia: list[Annotated[str, Field(min_length=1, max_length=30, pattern=WZOR_SLOWA)]] = Field(default_factory=list, max_length=15)
    opis: str = Field(default="", max_length=120)
    wymagaj_oznaczenia_hali: bool = True


class Logowanie(BaseModel):
    model_config = ConfigDict(extra="forbid")

    haslo: str = Field(min_length=1, max_length=200)


class DoUkrycia(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: HttpUrl = Field(max_length=2000)


class Wyszukiwanie:
    def __init__(self, zapytanie, profil):
        self.id = uuid.uuid4().hex
        self.zapytanie = zapytanie
        self.profil = profil
        self.stan = "trwa"
        self.start = time.time()
        self.koniec = None
        self.zdarzenia = []
        self.wyniki = {}
        self.przerwanie = threading.Event()
        self._blokada = threading.Lock()

    @property
    def zakonczone(self):
        return self.stan != "trwa"

    def dodaj(self, typ, dane):
        with self._blokada:
            self.zdarzenia.append({"id": len(self.zdarzenia), "typ": typ, "czas": round(time.time() - self.start, 2), "dane": dane})
            if typ == "koniec":
                self.wyniki[dane["rozmiar"]] = dane["wyniki"]

    def od(self, numer):
        with self._blokada:
            return self.zdarzenia[numer:]

    def opis(self):
        return {
            "id": self.id,
            "stan": self.stan,
            "marka": self.zapytanie.marka,
            "model": self.zapytanie.model,
            "nazwa": self.profil.nazwa,
            "profil": self.profil.slug,
            "rozmiary": self.zapytanie.rozmiary,
            "zdarzen": len(self.zdarzenia),
            "czas": round((self.koniec or time.time()) - self.start, 1),
            "gotowe_rozmiary": sorted(self.wyniki),
        }


class Menedzer:
    def __init__(self, wykonaj):
        self.wykonaj = wykonaj
        self.wyszukiwania = OrderedDict()
        self.aktywne = None
        self._blokada = threading.Lock()

    def uruchom(self, zapytanie, profil):
        with self._blokada:
            if self.aktywne and not self.aktywne.zakonczone:
                return None
            w = Wyszukiwanie(zapytanie, profil)
            self.aktywne = w
            self.wyszukiwania[w.id] = w
            while len(self.wyszukiwania) > PAMIETANE_WYSZUKIWANIA:
                self.wyszukiwania.popitem(last=False)
        threading.Thread(target=self._praca, args=(w,), daemon=True, name=f"wyszukiwanie-{w.id[:8]}").start()
        return w

    def _praca(self, w):
        z = w.zapytanie
        w.dodaj("wyszukiwanie_start", {"id": w.id, "nazwa": w.profil.nazwa, "rozmiary": z.rozmiary})
        stan = "gotowe"
        for rozmiar in z.rozmiary:
            opcje = przebieg.Opcje(
                rozmiar=rozmiar,
                zrodla=z.zrodla,
                max_cena=z.max_cena,
                tylko_pewne=z.tylko_pewne,
                odswiez=z.odswiez,
                reset_blokad=z.reset_blokad,
                pokaz_ukryte=z.pokaz_ukryte,
                przerwanie=w.przerwanie,
            )
            try:
                self.wykonaj(w.profil, opcje, w.dodaj)
            except przebieg.BrakZrodel as e:
                w.dodaj("blad", {"rozmiar": rozmiar, "komunikat": str(e)})
                stan = "blad"
                break
            except Exception as e:
                w.dodaj("blad", {"rozmiar": rozmiar, "komunikat": f"wyszukiwanie przerwane: {e.__class__.__name__}"})
                stan = "blad"
                break
            if w.przerwanie.is_set():
                stan = "przerwane"
                break
        w.koniec = time.time()
        w.dodaj("wyszukiwanie_koniec", {"stan": stan, "czas": round(w.koniec - w.start, 1), "gotowe_rozmiary": sorted(w.wyniki)})
        w.stan = stan

    def znajdz(self, identyfikator):
        w = self.wyszukiwania.get(identyfikator)
        if not w:
            raise HTTPException(404, "nie ma wyszukiwania o takim id")
        return w


def _sse(zdarzenie):
    return f"id: {zdarzenie['id']}\nevent: {zdarzenie['typ']}\ndata: {json.dumps(zdarzenie, ensure_ascii=False)}\n\n"


def _profil(marka, model):
    try:
        return katalog.profil(marka, model)
    except katalog.BladKatalogu as e:
        raise HTTPException(404, str(e)) from e


def _model_3d(marka, model):
    plik = U.KATALOG_MODELI_3D / f"{marka.id}-{model.id}.glb"
    return f"/modele/{plik.name}" if plik.is_file() else None


def _opis_katalogu():
    return {
        "rozmiary": katalog.rozmiary(),
        "marki": [
            {
                "id": m.id,
                "nazwa": m.nazwa,
                "modele": [
                    {
                        "id": mo.id,
                        "nazwa": mo.nazwa,
                        "model": mo.dane["model"],
                        "opis_wykluczen": mo.dane.get("opis_wykluczen") or m.dane.get("opis_wykluczen", ""),
                        "wskazowka_zdjec": mo.dane.get("wskazowka_zdjec", ""),
                        "model3d": _model_3d(m, mo),
                        "wlasny": bool(mo.dane.get("wlasny")),
                    }
                    for mo in m.modele
                ],
            }
            for m in katalog.marki()
        ],
    }


def utworz(wykonaj=przebieg.wykonaj, hosty=HOSTY, interfejs=None, administrator=None):
    interfejs = U.KATALOG_INTERFEJSU if interfejs is None else interfejs
    przebieg.wczytaj_env()
    app = FastAPI(title="Szatnia API", docs_url="/api/dokumentacja", redoc_url=None, openapi_url="/api/openapi.json")
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(hosty))
    menedzer = Menedzer(wykonaj)
    administrator = administrator or A.Administrator()

    def wymagaj_admina(request: Request):
        if not administrator.sprawdz(request.cookies.get(A.CIASTKO)):
            raise HTTPException(401, "tylko administrator może zmieniać modele, zaloguj się na stronie /admin.html")
    app.state.menedzer = menedzer

    @app.middleware("http")
    async def ochrona(request: Request, nastepny):
        zrodlo = request.headers.get("origin")
        ta_sama_strona = zrodlo and urlsplit(zrodlo).netloc == request.headers.get("host")
        if zrodlo and not ta_sama_strona and zrodlo not in DOZWOLONE_ZRODLA_STRON:
            return JSONResponse({"detail": "żądanie z obcej strony"}, status_code=403)
        odpowiedz = await nastepny(request)
        odpowiedz.headers.update(NAGLOWKI_BEZPIECZENSTWA)
        return odpowiedz

    @app.get("/api/zdrowie")
    def zdrowie():
        aktywne = menedzer.aktywne
        return {"ok": True, "aktywne": aktywne.id if aktywne and not aktywne.zakonczone else None}

    @app.get("/api/katalog")
    def opis_katalogu():
        return _opis_katalogu()

    @app.get("/api/katalog/{marka}/{model}/zrodla")
    def zrodla(marka: str, model: str):
        return przebieg.opis_zrodel(_profil(marka, model))

    @app.get("/api/katalog/{marka}/{model}/wyniki/{rozmiar}")
    def ostatnie_wyniki(marka: str, model: str, rozmiar: str):
        if rozmiar not in katalog.rozmiary():
            raise HTTPException(404, "nieobsługiwany rozmiar")
        plik = _profil(marka, model).katalog_wynikow(rozmiar) / "oferty.json"
        try:
            return json.loads(plik.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise HTTPException(404, "ten model w tym rozmiarze nie był jeszcze szukany") from e

    @app.get("/api/admin")
    def stan_admina(request: Request):
        return {"zalogowany": administrator.sprawdz(request.cookies.get(A.CIASTKO)), "skonfigurowany": administrator.skonfigurowany}

    @app.post("/api/admin/logowanie")
    def logowanie(dane: Logowanie, request: Request):
        if not administrator.skonfigurowany:
            raise HTTPException(503, "hasło administratora nie jest ustawione, uruchom: py serwer.py --ustaw-haslo")
        try:
            token = administrator.zaloguj(dane.haslo, request.client.host if request.client else "?")
        except A.ZaDuzoProb as e:
            raise HTTPException(429, "za dużo prób logowania, spróbuj za 15 minut") from e
        if not token:
            raise HTTPException(401, "nieprawidłowe hasło")
        odpowiedz = JSONResponse({"zalogowany": True})
        odpowiedz.set_cookie(A.CIASTKO, token, max_age=A.CZAS_SESJI, httponly=True, samesite="strict", secure=request.url.scheme == "https", path="/")
        return odpowiedz

    @app.post("/api/admin/wylogowanie")
    def wylogowanie(request: Request):
        administrator.wyloguj(request.cookies.get(A.CIASTKO))
        odpowiedz = JSONResponse({"zalogowany": False})
        odpowiedz.delete_cookie(A.CIASTKO, path="/")
        return odpowiedz

    @app.get("/api/wlasne")
    def lista_wlasnych():
        return wlasne.wczytaj()

    @app.post("/api/wlasne", status_code=201, dependencies=[Depends(wymagaj_admina)])
    def dodaj_wlasny(nowy: NowyModel):
        try:
            marka_id, model_id = wlasne.dodaj(nowy.marka, nowy.model, nowy.wykluczenia, nowy.opis, nowy.wymagaj_oznaczenia_hali, katalog.marki())
        except wlasne.BladWlasnych as e:
            raise HTTPException(e.kod, str(e)) from e
        return {"marka": marka_id, "model": model_id}

    @app.delete("/api/wlasne/{marka}/{model}", status_code=204, dependencies=[Depends(wymagaj_admina)])
    def usun_wlasny(marka: str, model: str):
        if not wlasne.usun(marka, model):
            raise HTTPException(404, "nie ma takiego własnego modelu")
        return Response(status_code=204)

    @app.post("/api/wyszukiwania", status_code=202)
    def nowe_wyszukiwanie(zapytanie: Zapytanie):
        dozwolone = katalog.rozmiary()
        zle = [r for r in zapytanie.rozmiary if r not in dozwolone]
        if zle:
            raise HTTPException(422, f"nieobsługiwane rozmiary: {', '.join(zle)}; dostępne {dozwolone[0]}–{dozwolone[-1]}")
        zapytanie.rozmiary = sorted(set(zapytanie.rozmiary), key=dozwolone.index)
        w = menedzer.uruchom(zapytanie, _profil(zapytanie.marka, zapytanie.model))
        if w is None:
            raise HTTPException(409, "trwa już inne wyszukiwanie, poczekaj na jego koniec")
        return {**w.opis(), "zdarzenia": f"/api/wyszukiwania/{w.id}/zdarzenia"}

    @app.get("/api/wyszukiwania/{identyfikator}")
    def stan_wyszukiwania(identyfikator: str):
        w = menedzer.znajdz(identyfikator)
        return {**w.opis(), "wyniki": w.wyniki}

    @app.get("/api/wyszukiwania/{identyfikator}/zdarzenia")
    async def zdarzenia(identyfikator: str, request: Request, od: int = 0):
        w = menedzer.znajdz(identyfikator)
        ostatnie = request.headers.get("last-event-id")
        numer = int(ostatnie) + 1 if ostatnie and ostatnie.isdigit() else max(0, od)

        async def strumien():
            nonlocal numer
            ping = time.monotonic()
            while True:
                nowe = w.od(numer)
                for z in nowe:
                    yield _sse(z)
                numer += len(nowe)
                if w.zakonczone and not w.od(numer):
                    return
                if await request.is_disconnected():
                    return
                if time.monotonic() - ping > PING_CO_SEKUND:
                    ping = time.monotonic()
                    yield ": ping\n\n"
                await asyncio.sleep(0.2)

        return StreamingResponse(strumien(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.post("/api/wyszukiwania/{identyfikator}/przerwij", status_code=202)
    def przerwij(identyfikator: str):
        w = menedzer.znajdz(identyfikator)
        if w.zakonczone:
            raise HTTPException(409, "to wyszukiwanie już się zakończyło")
        if not w.przerwanie.is_set():
            w.przerwanie.set()
            w.dodaj("przerywanie", {})
        return w.opis()

    @app.post("/api/ukryte")
    def ukryj(wpis: DoUkrycia):
        dodane = ukryte.dodaj(U.PLIK_UKRYTYCH, [str(wpis.url)])
        return {"ukryto": bool(dodane)}

    @app.post("/api/ukryte/przywroc")
    def przywroc(wpis: DoUkrycia):
        return {"przywrocono": bool(ukryte.usun(U.PLIK_UKRYTYCH, [str(wpis.url)]))}

    @app.api_route("/api/{reszta:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
    def nieznany_adres_api(reszta: str):
        raise HTTPException(404, "nie ma takiego adresu API")

    if U.KATALOG_MODELI_3D.is_dir():
        app.mount("/modele", StaticFiles(directory=U.KATALOG_MODELI_3D), name="modele")
    if interfejs and interfejs.is_dir():
        app.mount("/", StaticFiles(directory=interfejs, html=True), name="interfejs")

    return app
