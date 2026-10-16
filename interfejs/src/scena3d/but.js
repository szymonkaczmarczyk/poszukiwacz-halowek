import * as THREE from "three";

export const DLUGOSC = 2.8;
export const PIETA_X = -DLUGOSC / 2;
const WYKLADNIK_PRZEKROJU = 2.25;
const OTWOR_OD = 0.05;
const OTWOR_DO = 0.33;
const KOLOR_WNETRZA = 0.12;
const GRUBOSC_PODESZWY = 0.13;

const WYSOKOSC = [
  [0, 0.66],
  [0.06, 0.78],
  [0.14, 0.8],
  [0.27, 0.64],
  [0.36, 0.68],
  [0.44, 0.7],
  [0.62, 0.52],
  [0.8, 0.34],
  [0.9, 0.25],
  [0.97, 0.15],
  [1, 0.06],
];

const SZEROKOSC = [
  [0, 0.1],
  [0.03, 0.27],
  [0.09, 0.33],
  [0.25, 0.35],
  [0.5, 0.42],
  [0.7, 0.47],
  [0.86, 0.43],
  [0.95, 0.32],
  [1, 0.06],
];

function interpolacja(punkty) {
  const styczne = punkty.map((p, i) => {
    const a = punkty[Math.max(0, i - 1)];
    const b = punkty[Math.min(punkty.length - 1, i + 1)];
    return (b[1] - a[1]) / (b[0] - a[0] || 1);
  });
  return (t) => {
    const nastepny = punkty.findIndex((p) => p[0] > t);
    const k = Math.min(punkty.length - 2, Math.max(0, (nastepny === -1 ? punkty.length : nastepny) - 1));
    const [t0, v0] = punkty[k];
    const [t1, v1] = punkty[k + 1];
    const d = t1 - t0;
    const u = Math.min(1, Math.max(0, (t - t0) / d));
    const u2 = u * u;
    const u3 = u2 * u;
    return (2 * u3 - 3 * u2 + 1) * v0 + (u3 - 2 * u2 + u) * d * styczne[k] + (-2 * u3 + 3 * u2) * v1 + (u3 - u2) * d * styczne[k + 1];
  };
}

export const wysokosc = interpolacja(WYSOKOSC);
export const szerokosc = interpolacja(SZEROKOSC);

function otwarcie(t) {
  if (t <= OTWOR_OD || t >= OTWOR_DO) return 0;
  return Math.sin((Math.PI * (t - OTWOR_OD)) / (OTWOR_DO - OTWOR_OD));
}

function wglebienie(t, theta) {
  const o = otwarcie(t);
  if (!o) return 0;
  const polowaKata = Math.PI * 0.3 * o ** 0.5;
  const odSrodka = Math.abs(theta - Math.PI / 2);
  if (odSrodka >= polowaKata) return 0;
  const k = 1 - odSrodka / polowaKata;
  return k * k * (3 - 2 * k) * o ** 0.6;
}

function punktPrzekroju(t, theta, skala = 1, zOtworem = false) {
  const c = Math.cos(theta);
  const s = Math.sin(theta);
  const w = szerokosc(t) * skala;
  const h = wysokosc(t) * skala;
  const potega = 2 / WYKLADNIK_PRZEKROJU;
  const g = zOtworem ? wglebienie(t, theta) : 0;
  return new THREE.Vector3(PIETA_X + DLUGOSC * t, h * Math.abs(s) ** potega - 0.42 * g, w * (1 - 0.12 * g) * Math.sign(c) * Math.abs(c) ** potega);
}

export function powierzchnia({ t0 = 0, t1 = 1, theta0 = 0, theta1 = Math.PI, skala = 1, podzialT = 72, podzialTheta = 36, zOtworem = false }) {
  const pozycje = [];
  const kolory = [];
  const uv = [];
  const indeksy = [];
  for (let i = 0; i <= podzialT; i++) {
    const t = t0 + ((t1 - t0) * i) / podzialT;
    for (let j = 0; j <= podzialTheta; j++) {
      const theta = theta0 + ((theta1 - theta0) * j) / podzialTheta;
      const p = punktPrzekroju(t, theta, skala, zOtworem);
      pozycje.push(p.x, p.y, p.z);
      const jasnosc = zOtworem ? 1 - (1 - KOLOR_WNETRZA) * Math.min(1, wglebienie(t, theta) * 2.2) : 1;
      kolory.push(jasnosc, jasnosc, jasnosc);
      uv.push(i / podzialT, j / podzialTheta);
    }
  }
  const rzad = podzialTheta + 1;
  for (let i = 0; i < podzialT; i++) {
    for (let j = 0; j < podzialTheta; j++) {
      const a = i * rzad + j;
      const b = a + rzad;
      indeksy.push(a, b, a + 1, b, b + 1, a + 1);
    }
  }
  const geometria = new THREE.BufferGeometry();
  geometria.setAttribute("position", new THREE.Float32BufferAttribute(pozycje, 3));
  geometria.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
  geometria.setAttribute("color", new THREE.Float32BufferAttribute(kolory, 3));
  geometria.setIndex(indeksy);
  geometria.computeVertexNormals();
  return geometria;
}

function podeszwa() {
  const obrys = new THREE.Shape();
  const kroki = 80;
  for (let i = 0; i <= kroki; i++) {
    const t = i / kroki;
    const x = PIETA_X + DLUGOSC * t;
    const z = szerokosc(t) * 1.04;
    if (i === 0) obrys.moveTo(x, z);
    else obrys.lineTo(x, z);
  }
  for (let i = kroki; i >= 0; i--) {
    const t = i / kroki;
    obrys.lineTo(PIETA_X + DLUGOSC * t, -szerokosc(t) * 1.04);
  }
  const geometria = new THREE.ExtrudeGeometry(obrys, {
    depth: GRUBOSC_PODESZWY,
    bevelEnabled: true,
    bevelThickness: 0.025,
    bevelSize: 0.03,
    bevelSegments: 4,
    curveSegments: 64,
  });
  geometria.rotateX(Math.PI / 2);
  geometria.computeVertexNormals();
  return geometria;
}

function sznurowki() {
  const geometrie = [];
  for (let k = 0; k < 5; k++) {
    const t = 0.45 + k * 0.042;
    const punkty = [];
    for (let j = 0; j <= 12; j++) {
      const theta = Math.PI * (0.36 + (0.28 * j) / 12);
      punkty.push(punktPrzekroju(t, theta, 1.035));
    }
    geometrie.push(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(punkty), 24, 0.013, 6, false));
  }
  return geometrie;
}

export function zbudujBut(materialy) {
  const but = new THREE.Group();
  const czesci = [
    ["cholewka", new THREE.Mesh(powierzchnia({ podzialT: 120, podzialTheta: 56, zOtworem: true }), materialy.cholewka)],
    ["nosek", new THREE.Mesh(powierzchnia({ t0: 0.82, t1: 1, skala: 1.01, podzialT: 28 }), materialy.nosek)],
    ["zapietek", new THREE.Mesh(powierzchnia({ t0: 0, t1: 0.2, theta1: Math.PI * 0.3, skala: 1.012, podzialT: 28, podzialTheta: 14 }), materialy.zapietek)],
    ["zapietek", new THREE.Mesh(powierzchnia({ t0: 0, t1: 0.2, theta0: Math.PI * 0.7, skala: 1.012, podzialT: 28, podzialTheta: 14 }), materialy.zapietek)],
    ["pas", new THREE.Mesh(powierzchnia({ t0: 0.34, t1: 0.74, theta0: Math.PI * 0.14, theta1: Math.PI * 0.21, skala: 1.008, podzialT: 40, podzialTheta: 4 }), materialy.pas)],
    ["pas", new THREE.Mesh(powierzchnia({ t0: 0.34, t1: 0.74, theta0: Math.PI * 0.79, theta1: Math.PI * 0.86, skala: 1.008, podzialT: 40, podzialTheta: 4 }), materialy.pas)],
    ["podeszwa", new THREE.Mesh(podeszwa(), materialy.podeszwa)],
    ...sznurowki().map((g) => ["sznurowka", new THREE.Mesh(g, materialy.sznurowki)]),
  ];
  for (const [nazwa, siatka] of czesci) {
    siatka.name = nazwa;
    siatka.castShadow = true;
    siatka.receiveShadow = true;
    but.add(siatka);
  }
  but.position.y = GRUBOSC_PODESZWY + 0.025;
  return but;
}
