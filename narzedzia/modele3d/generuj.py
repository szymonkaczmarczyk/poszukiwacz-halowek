import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
import numpy as np
import trimesh
from gradio_client import Client, handle_file
from scipy import ndimage

PROJEKT = Path(__file__).resolve().parents[2]
ZDJECIA = PROJEKT / "models"
MODELE = PROJEKT / "interfejs" / "public" / "modele"
WYBOR = Path(__file__).with_name("wybor_zdjec.json")
SPACE = "trellis-community/TRELLIS"
ROZSZERZENIA = {".jpg", ".jpeg", ".png", ".webp"}
PROBY_SIECI = 3
PRZERWA_PO_BLEDZIE = 60
LIMIT_CZASU = httpx.Timeout(900, connect=60)

WARSTWA_DOLNA = 0.085
WARSTWA_GORNYCH = 0.14
PAS_OBRYSU = 0.32
PROG_NORMALNEJ = 0.55
SIATKA = 200


def token_z_env():
    try:
        for linia in (PROJEKT / ".env").read_text(encoding="utf-8").splitlines():
            if linia.startswith("HF_TOKEN="):
                return linia.split("=", 1)[1].strip().strip('"').strip("'") or None
    except OSError:
        return None
    return None


def usun_tlo_pod_butem(siatka):
    v, f = siatka.vertices, siatka.faces
    ymin, ymax = v[:, 1].min(), v[:, 1].max()
    wysokosc = ymax - ymin
    granica = ymin + WARSTWA_DOLNA * wysokosc
    xz = v[:, [0, 2]]
    lo, hi = xz.min(0), xz.max(0)
    komorka = (hi - lo).max() / SIATKA

    def indeks(punkty):
        return np.clip(((punkty - lo) / komorka).astype(int), 0, SIATKA - 1)

    dol_buta = (v[:, 1] > granica) & (v[:, 1] < ymin + PAS_OBRYSU * wysokosc)
    obrys = np.zeros((SIATKA, SIATKA), bool)
    i = indeks(xz[dol_buta])
    obrys[i[:, 0], i[:, 1]] = True
    obrys = ndimage.binary_dilation(ndimage.binary_fill_holes(ndimage.binary_closing(obrys, iterations=3)), iterations=2)
    wierzcholki_scian = v[f]
    dolne = (wierzcholki_scian[:, :, 1] <= granica).all(1)
    j = indeks(wierzcholki_scian.mean(1)[:, [0, 2]])
    poza_obrysem = ~obrys[j[:, 0], j[:, 1]]
    nisko = (wierzcholki_scian[:, :, 1] <= ymin + WARSTWA_GORNYCH * wysokosc).all(1)
    do_gory = siatka.face_normals[:, 1] > PROG_NORMALNEJ
    usun = (dolne & poza_obrysem) | (nisko & do_gory)
    siatka.update_faces(~usun)
    siatka.remove_unreferenced_vertices()
    return int(usun.sum())


class BrakTekstury(Exception):
    pass


def liczba_obrazow(plik):
    dane = Path(plik).read_bytes()
    dlugosc = int.from_bytes(dane[12:16], "little")
    return len(json.loads(dane[20:20 + dlugosc]).get("images", []))


def pobierz_glb(plik, cel, token):
    if isinstance(plik, (str, Path)) and Path(str(plik)).exists():
        shutil.copy(plik, cel)
        return
    adres = plik.get("url") if isinstance(plik, dict) else str(plik)
    naglowki = {"Authorization": f"Bearer {token}"} if token else {}
    with httpx.stream("GET", adres, headers=naglowki, timeout=LIMIT_CZASU, follow_redirects=True) as odpowiedz:
        odpowiedz.raise_for_status()
        with open(cel, "wb") as plik_wyjsciowy:
            for kawalek in odpowiedz.iter_bytes():
                plik_wyjsciowy.write(kawalek)


def blad_sieci(e):
    return isinstance(e, (httpx.TransportError, TimeoutError, ConnectionError)) or type(e).__name__ in {"CancelledError", "RemoteProtocolError"}


def generuj(klucz, indeksy, token, robocze):
    zdjecia = sorted(p for p in (ZDJECIA / klucz).iterdir() if p.suffix.lower() in ROZSZERZENIA)
    wybrane = [zdjecia[i] for i in indeksy]
    klient = Client(SPACE, verbose=False, token=token, download_files=False, httpx_kwargs={"timeout": LIMIT_CZASU})
    klient.predict(api_name="/start_session")
    wynik = klient.predict(
        image=handle_file(str(wybrane[0])),
        multiimages=[{"image": handle_file(str(p)), "caption": None} for p in wybrane],
        seed=0,
        ss_guidance_strength=7.5,
        ss_sampling_steps=12,
        slat_guidance_strength=3.0,
        slat_sampling_steps=12,
        multiimage_algo="stochastic",
        mesh_simplify=0.95,
        texture_size=1024,
        api_name="/generate_and_extract_glb",
    )
    surowy = robocze / "surowy.glb"
    pobierz_glb(wynik[2] or wynik[1], surowy, token)
    scena = trimesh.load(surowy, force="scene")
    usuniete = sum(usun_tlo_pod_butem(g) for g in scena.geometry.values())
    czysty = robocze / "czysty.glb"
    scena.export(czysty)
    if liczba_obrazow(surowy) and not liczba_obrazow(czysty):
        raise BrakTekstury("tekstura zginęła przy usuwaniu tła, sprawdź, czy w środowisku jest Pillow")
    cel = MODELE / f"{klucz.replace('/', '-')}.glb"
    subprocess.run(
        ["npx", "--yes", "@gltf-transform/cli@4", "optimize", str(czysty), str(cel), "--compress", "meshopt", "--texture-compress", "webp", "--texture-size", "1024"],
        check=True,
        capture_output=True,
    )
    if liczba_obrazow(czysty) and not liczba_obrazow(cel):
        cel.unlink()
        raise BrakTekstury("tekstura zginęła przy kompresji")
    return cel, usuniete


def main():
    p = argparse.ArgumentParser(description="Generuje modele 3D butów ze zdjęć w models/ (TRELLIS na Hugging Face) i zapisuje je w interfejs/public/modele/.")
    p.add_argument("modele", nargs="*", help="np. nike/gato; bez podania wszystkie brakujące")
    p.add_argument("--od-nowa", action="store_true", help="generuj także modele, które już mają plik GLB")
    p.add_argument("--brakujace", action="store_true", help="tylko wypisz modele bez pliku GLB i zakończ (kod 0, gdy nie brakuje żadnego)")
    a = p.parse_args()
    wybor = json.loads(WYBOR.read_text(encoding="utf-8"))
    if a.brakujace:
        brak = [k for k in wybor if not (MODELE / f"{k.replace('/', '-')}.glb").exists()]
        print(f"Brakuje {len(brak)} z {len(wybor)}: {', '.join(brak)}" if brak else f"Wszystkie {len(wybor)} modele są gotowe.")
        return 1 if brak else 0
    token = token_z_env()
    print(f"{time.strftime('%Y-%m-%d %H:%M')} Token Hugging Face: {'jest' if token else 'brak, limit anonimowy'}", flush=True)
    MODELE.mkdir(parents=True, exist_ok=True)
    for klucz, indeksy in wybor.items():
        if a.modele and klucz not in a.modele:
            continue
        cel = MODELE / f"{klucz.replace('/', '-')}.glb"
        if cel.exists() and not a.od_nowa:
            continue
        for proba in range(1, PROBY_SIECI + 1):
            start = time.time()
            try:
                with tempfile.TemporaryDirectory() as robocze:
                    cel, usuniete = generuj(klucz, indeksy, token, Path(robocze))
                print(f"{klucz}: gotowe w {time.time() - start:.0f} s, {cel.stat().st_size // 1024} KB, usunięto {usuniete} trójkątów tła", flush=True)
                break
            except Exception as e:
                print(f"{klucz}: błąd {type(e).__name__} (próba {proba} z {PROBY_SIECI}): {str(e)[:200]}", flush=True)
                if "quota" in str(e).lower():
                    print("Limit GPU na dziś wyczerpany. Uruchom ponownie jutro, gotowe modele zostaną pominięte.")
                    return 3
                if not blad_sieci(e) or proba == PROBY_SIECI:
                    break
                time.sleep(PRZERWA_PO_BLEDZIE * proba)
    return 0


if __name__ == "__main__":
    sys.exit(main())
