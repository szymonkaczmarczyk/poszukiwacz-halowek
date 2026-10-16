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

function wyrownaj(scena) {
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
