import * as THREE from "three";
import { DLUGOSC, PIETA_X } from "./but.js";

const ROZMIAR_BAZOWY = 42;
const SZEROKOSC_PX = 1024;
const WYSOKOSC_PX = 400;
const MARGINES = 0.5;
const KOLORY = { linia: "#5a5c66", tekst: "#c9c7c1", akcent: "#8eadff", tlo: "rgba(110,149,255,0.16)" };

export function pozycjaRozmiaru(rozmiar) {
  return PIETA_X + (DLUGOSC * Number(rozmiar)) / ROZMIAR_BAZOWY;
}

export function skalaRozmiaru(rozmiary) {
  if (!rozmiary.length) return 1;
  return Math.max(...rozmiary.map(Number)) / ROZMIAR_BAZOWY;
}

export function utworzMiarke(rozmiary) {
  const poczatek = pozycjaRozmiaru(Number(rozmiary[0]) - MARGINES);
  const koniec = pozycjaRozmiaru(Number(rozmiary.at(-1)) + MARGINES);
  const szerokosc = koniec - poczatek;
  const wysokosc = (szerokosc * WYSOKOSC_PX) / SZEROKOSC_PX;
  const plotno = document.createElement("canvas");
  plotno.width = SZEROKOSC_PX;
  plotno.height = WYSOKOSC_PX;
  const kontekst = plotno.getContext("2d");
  const tekstura = new THREE.CanvasTexture(plotno);
  tekstura.colorSpace = THREE.SRGBColorSpace;
  tekstura.anisotropy = 8;
  const material = new THREE.MeshBasicMaterial({ map: tekstura, transparent: true, opacity: 0, depthWrite: false, toneMapped: false });
  const siatka = new THREE.Mesh(new THREE.PlaneGeometry(szerokosc, wysokosc), material);
  siatka.rotation.x = -Math.PI / 2;
  siatka.position.set(poczatek + szerokosc / 2, 0.003, 0.56 + wysokosc / 2);
  siatka.renderOrder = 2;

  const naPiksel = (x) => ((x - poczatek) / szerokosc) * SZEROKOSC_PX;
  const kroj = getComputedStyle(document.body).fontFamily;

  function rysuj(wybrane) {
    kontekst.clearRect(0, 0, SZEROKOSC_PX, WYSOKOSC_PX);
    const y = 70;
    kontekst.strokeStyle = KOLORY.linia;
    kontekst.lineWidth = 4;
    kontekst.beginPath();
    kontekst.moveTo(0, y);
    kontekst.lineTo(SZEROKOSC_PX, y);
    kontekst.stroke();
    kontekst.textAlign = "center";
    kontekst.textBaseline = "top";
    for (const rozmiar of rozmiary) {
      const x = naPiksel(pozycjaRozmiaru(rozmiar));
      const zaznaczony = wybrane.includes(rozmiar);
      if (zaznaczony) {
        kontekst.fillStyle = KOLORY.tlo;
        kontekst.fillRect(x - 44, 0, 88, WYSOKOSC_PX);
      }
      kontekst.strokeStyle = zaznaczony ? KOLORY.akcent : KOLORY.linia;
      kontekst.lineWidth = zaznaczony ? 8 : 4;
      kontekst.beginPath();
      kontekst.moveTo(x, zaznaczony ? 0 : y - 34);
      kontekst.lineTo(x, y + 34);
      kontekst.stroke();
      kontekst.fillStyle = zaznaczony ? KOLORY.akcent : KOLORY.tekst;
      kontekst.font = `${zaznaczony ? 750 : 550} 72px ${kroj}`;
      kontekst.fillText(rozmiar, x, y + 58);
    }
    tekstura.needsUpdate = true;
  }

  return { siatka, rysuj };
}
