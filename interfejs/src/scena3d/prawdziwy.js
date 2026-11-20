import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/examples/jsm/libs/meshopt_decoder.module.js";
import { DLUGOSC, PIETA_X } from "./but.js";

const ladowarka = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
const pamiec = new Map();

function wierzcholki(obiekt) {
  const punkty = [];
  const p = new THREE.Vector3();
  obiekt.updateWorldMatrix(true, true);
  obiekt.traverse((dziecko) => {
    if (!dziecko.isMesh) return;
    const pozycje = dziecko.geometry.attributes.position;
    const krok = Math.max(1, Math.floor(pozycje.count / 4000));
    for (let i = 0; i < pozycje.count; i += krok) punkty.push(p.fromBufferAttribute(pozycje, i).applyMatrix4(dziecko.matrixWorld).clone());
  });
  return punkty;
}

function pietaZPrzodu(punkty) {
  const granica = DLUGOSC * 0.25;
  const najwyzej = (lista) => lista.reduce((max, p) => Math.max(max, p.y), -Infinity);
  const przod = punkty.filter((p) => p.x > granica);
  const tyl = punkty.filter((p) => p.x < -granica);
  return przod.length > 0 && tyl.length > 0 && najwyzej(przod) > najwyzej(tyl);
}

const DOKLADNOSC_SCALANIA = 20000;
const MIN_DLUGOSC_ODPRYSKU = 0.1;
const ZAPAS_OBRYSU = 0.03;

function skladowe(geometria) {
  const pozycje = geometria.attributes.position;
  const indeks = geometria.index;
  const trojkaty = (indeks ? indeks.count : pozycje.count) / 3;
  const wierzcholek = (t, k) => (indeks ? indeks.getX(t * 3 + k) : t * 3 + k);
  geometria.computeBoundingBox();
  const krok = geometria.boundingBox.getSize(new THREE.Vector3()).length() / DOKLADNOSC_SCALANIA || 1;
  const klucze = new Map();
  const rodzic = new Int32Array(pozycje.count);
  for (let i = 0; i < pozycje.count; i++) {
    const klucz = `${Math.round(pozycje.getX(i) / krok)},${Math.round(pozycje.getY(i) / krok)},${Math.round(pozycje.getZ(i) / krok)}`;
    if (!klucze.has(klucz)) klucze.set(klucz, i);
    rodzic[i] = klucze.get(klucz);
  }
  const korzen = (x) => {
    while (rodzic[x] !== x) {
      rodzic[x] = rodzic[rodzic[x]];
      x = rodzic[x];
    }
    return x;
  };
  for (let t = 0; t < trojkaty; t++) {
    const a = korzen(wierzcholek(t, 0));
    for (const k of [1, 2]) {
      const b = korzen(wierzcholek(t, k));
      if (b !== a) rodzic[b] = a;
    }
  }
  const grupy = new Map();
  const punkt = new THREE.Vector3();
  for (let t = 0; t < trojkaty; t++) {
    const id = korzen(wierzcholek(t, 0));
    if (!grupy.has(id)) grupy.set(id, { trojkaty: [], obrys: new THREE.Box3() });
    const grupa = grupy.get(id);
    grupa.trojkaty.push(t);
    for (const k of [0, 1, 2]) grupa.obrys.expandByPoint(punkt.fromBufferAttribute(pozycje, wierzcholek(t, k)));
  }
  return { grupy: [...grupy.values()], wierzcholek };
}

function usunOdpryski(geometria) {
  const { grupy, wierzcholek } = skladowe(geometria);
  if (grupy.length < 2) return;
  grupy.sort((a, b) => b.trojkaty.length - a.trojkaty.length);
  const glowny = grupy[0].obrys;
  const dlugosc = (obrys) => Math.max(...obrys.getSize(new THREE.Vector3()).toArray());
  const zasieg = dlugosc(glowny);
  const dozwolony = glowny.clone().expandByScalar(zasieg * ZAPAS_OBRYSU);
  const odpryski = grupy.filter((g) => dlugosc(g.obrys) > zasieg * MIN_DLUGOSC_ODPRYSKU && !dozwolony.containsBox(g.obrys));
  if (!odpryski.length) return;
  const zostaja = grupy.filter((g) => !odpryski.includes(g));
  const nowyIndeks = [];
  for (const g of zostaja) for (const t of g.trojkaty) nowyIndeks.push(wierzcholek(t, 0), wierzcholek(t, 1), wierzcholek(t, 2));
  geometria.setIndex(nowyIndeks);
  geometria.computeBoundingBox();
  geometria.computeBoundingSphere();
}

function wyrownaj(scena) {
  scena.traverse((dziecko) => {
    if (dziecko.isMesh) usunOdpryski(dziecko.geometry);
  });
  const opakowanie = new THREE.Group();
  const korzen = new THREE.Group();
  korzen.add(scena);
  opakowanie.add(korzen);
  let pudelko = new THREE.Box3().setFromObject(korzen);
  let rozmiar = pudelko.getSize(new THREE.Vector3());
  if (rozmiar.z > rozmiar.x) korzen.rotation.y = Math.PI / 2;
  pudelko = new THREE.Box3().setFromObject(korzen);
  rozmiar = pudelko.getSize(new THREE.Vector3());
  korzen.scale.multiplyScalar(DLUGOSC / rozmiar.x);
  const wysrodkuj = () => {
    const b = new THREE.Box3().setFromObject(korzen);
    const srodek = b.getCenter(new THREE.Vector3());
    korzen.position.x -= srodek.x;
    korzen.position.z -= srodek.z;
    korzen.position.y -= b.min.y;
  };
  wysrodkuj();
  if (pietaZPrzodu(wierzcholki(korzen))) {
    korzen.rotation.y += Math.PI;
    wysrodkuj();
  }
  opakowanie.position.x = -PIETA_X;
  scena.traverse((dziecko) => {
    if (!dziecko.isMesh) return;
    dziecko.castShadow = true;
    dziecko.receiveShadow = true;
  });
  return opakowanie;
}

export function wczytajPrawdziwy(adres) {
  if (!pamiec.has(adres)) {
    pamiec.set(
      adres,
      ladowarka.loadAsync(adres).then((gltf) => wyrownaj(gltf.scene)),
    );
    pamiec.get(adres).catch(() => pamiec.delete(adres));
  }
  return pamiec.get(adres);
}
