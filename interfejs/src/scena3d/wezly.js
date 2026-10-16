import * as THREE from "three";
import { gsap } from "gsap";

const PROMIEN_ORBITY = 2.05;
const WYSOKOSC_ORBITY = 0.9;
const SRODEK_BUTA = new THREE.Vector3(0, 0.38, 0);
const KOLORY = {
  czeka: "#4a4c55",
  trwa: "#6e95ff",
  ok: "#45d19a",
  wstrzymane: "#f2c94c",
  podejrzane: "#f2c94c",
  "błąd": "#ff7a7a",
  przerwane: "#6b6a66",
};

export function utworzWezly() {
  const grupa = new THREE.Group();
  const geometria = new THREE.SphereGeometry(0.06, 24, 16);
  const wezly = new Map();
  let czas = 0;

  function wyczysc() {
    for (const w of wezly.values()) {
      grupa.remove(w.siatka, w.linia);
      w.material.dispose();
      w.linia.geometry.dispose();
      w.linia.material.dispose();
    }
    wezly.clear();
  }

  function ustaw(nazwy) {
    wyczysc();
    nazwy.forEach((nazwa, i) => {
      const kat = (i / nazwy.length) * Math.PI * 2;
      const pozycja = new THREE.Vector3(Math.cos(kat) * PROMIEN_ORBITY, WYSOKOSC_ORBITY + Math.sin(i * 1.7) * 0.22, Math.sin(kat) * PROMIEN_ORBITY * 0.8);
      const material = new THREE.MeshStandardMaterial({ color: KOLORY.czeka, emissive: KOLORY.czeka, emissiveIntensity: 0.5, roughness: 0.3 });
      const siatka = new THREE.Mesh(geometria, material);
      siatka.position.copy(pozycja);
      siatka.scale.setScalar(0.001);
      const linia = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints([pozycja, SRODEK_BUTA]),
        new THREE.LineBasicMaterial({ color: KOLORY.trwa, transparent: true, opacity: 0 }),
      );
      grupa.add(siatka, linia);
      wezly.set(nazwa, { siatka, material, linia, stan: "czeka", faza: i * 0.9 });
      gsap.to(siatka.scale, { x: 1, y: 1, z: 1, duration: 0.6, delay: i * 0.05, ease: "back.out(2.5)" });
    });
  }

  function zmienKolor(w, kolor) {
    const docelowy = new THREE.Color(kolor);
    gsap.to(w.material.color, { r: docelowy.r, g: docelowy.g, b: docelowy.b, duration: 0.5 });
    gsap.to(w.material.emissive, { r: docelowy.r, g: docelowy.g, b: docelowy.b, duration: 0.5 });
  }

  function stan(nazwa, nowy, ofert = 0) {
    const w = wezly.get(nazwa);
    if (!w) return;
    w.stan = nowy;
    zmienKolor(w, KOLORY[nowy] || KOLORY.czeka);
    if (nowy === "trwa") {
      gsap.to(w.linia.material, { opacity: 0.35, duration: 0.4 });
      w.linia.material.color.set(KOLORY.trwa);
      return;
    }
    w.linia.material.color.set(KOLORY[nowy] || KOLORY.czeka);
    gsap.killTweensOf(w.siatka.scale);
    const blysk = nowy === "ok" && ofert > 0 ? 2.2 : 1.4;
    gsap
      .timeline()
      .to(w.material, { emissiveIntensity: 1.6, duration: 0.15 })
      .to(w.siatka.scale, { x: blysk, y: blysk, z: blysk, duration: 0.2, ease: "power2.out" }, 0)
      .to(w.siatka.scale, { x: 1, y: 1, z: 1, duration: 0.7, ease: "elastic.out(1, 0.4)" })
      .to(w.material, { emissiveIntensity: 0.55, duration: 0.6 }, "<");
    const znalazlo = nowy === "ok" && ofert > 0;
    gsap
      .timeline()
      .to(w.linia.material, { opacity: znalazlo ? 0.5 : 0.08, duration: 0.3 })
      .to(w.linia.material, { opacity: znalazlo ? 0.16 : 0.04, duration: 1.4, delay: 0.2 });
  }

  function aktualizuj(dt) {
    czas += dt;
    grupa.rotation.y += dt * 0.18;
    for (const w of wezly.values()) {
      if (w.stan !== "trwa") continue;
      const puls = 1 + Math.sin(czas * 6 + w.faza) * 0.22;
      w.siatka.scale.setScalar(puls);
      w.material.emissiveIntensity = 0.7 + Math.sin(czas * 6 + w.faza) * 0.4;
    }
  }

  return {
    grupa,
    ustaw,
    stan,
    aktualizuj,
    get aktywne() {
      return [...wezly.values()].some((w) => w.stan === "trwa" || w.stan === "czeka");
    },
    get puste() {
      return wezly.size === 0;
    },
  };
}
