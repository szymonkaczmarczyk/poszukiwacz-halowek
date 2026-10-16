import * as THREE from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { pobierz, subskrybuj } from "../stan.js";
import { PIETA_X, zbudujBut } from "./but.js";
import { CZESCI, utworzMaterialy, zestaw } from "./materialy.js";
import { pozycjaRozmiaru, skalaRozmiaru, utworzMiarke } from "./miarka.js";
import { wczytajPrawdziwy } from "./prawdziwy.js";
import { utworzWezly } from "./wezly.js";

gsap.registerPlugin(ScrollTrigger);

const UJECIA = {
  hero: { kierunek: [3.4, 1.75, 3.9], cel: [0.05, 0.34, 0], kadr: 1.05, obrot: -0.45, krecenie: true },
  marka: { kierunek: [0.05, 0.28, 1], cel: [0.05, 0.36, 0], kadr: 1.02, obrot: 0 },
  model: { kierunek: [3, 1.3, 2.5], cel: [0.3, 0.32, 0], kadr: 0.92, obrot: 0.25 },
  rozmiar: { kierunek: [0.05, 2.4, 0.7], cel: [1.1, 0.05, 0.6], kadr: 0.4, obrot: 0, miarka: true },
  filtry: { kierunek: [-3.3, 1.55, 3.1], cel: [0, 0.34, 0], kadr: 1.02, obrot: -0.2 },
  postep: { kierunek: [3.2, 2.6, 4.7], cel: [0, 0.5, 0], kadr: 1.5, obrot: 0.6, krecenie: true },
};
const PELNY_OBROT = Math.PI * 2;
const PROMIEN_BUTA = 1.62;
const KLATKI_PO_ZMIANIE = 150;

function nazwaUjecia(sekcja) {
  if (sekcja.classList.contains("hero")) return "hero";
  if (sekcja.classList.contains("postep")) return "postep";
  return sekcja.dataset.krok;
}

export function uruchomScene3d(kontener, katalog) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.domElement.className = "scena__plotno";
  renderer.domElement.setAttribute("aria-hidden", "true");
  kontener.querySelector(".scena__marka").after(renderer.domElement);

  const scena = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scena.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scena.environmentIntensity = 0.55;

  const kamera = new THREE.PerspectiveCamera(30, 1, 0.1, 50);

  const kluczowe = new THREE.DirectionalLight("#fff6ea", 2.4);
  kluczowe.position.set(2.5, 5, 3);
  kluczowe.castShadow = true;
  kluczowe.shadow.mapSize.set(1024, 1024);
  kluczowe.shadow.camera.left = -3;
  kluczowe.shadow.camera.right = 3;
  kluczowe.shadow.camera.top = 3;
  kluczowe.shadow.camera.bottom = -3;
  kluczowe.shadow.bias = -0.0005;
  kluczowe.shadow.radius = 6;
  scena.add(kluczowe);

  const kontra = new THREE.SpotLight("#6e95ff", 18, 12, Math.PI / 5, 0.6, 1.4);
  kontra.position.set(-2.6, 2.4, -3.2);
  scena.add(kontra, kontra.target);
  scena.add(new THREE.HemisphereLight("#cfd6ff", "#0e0e10", 0.35));

  const podloga = new THREE.Mesh(new THREE.PlaneGeometry(16, 16), new THREE.ShadowMaterial({ opacity: 0.42, depthWrite: false }));
  podloga.rotation.x = -Math.PI / 2;
  podloga.renderOrder = -1;
  podloga.receiveShadow = true;
  scena.add(podloga);

  const stan0 = pobierz();
  const materialy = utworzMaterialy(stan0.marka);
  const obrot = new THREE.Group();
  const skok = new THREE.Group();
  const os = new THREE.Group();
  const but = zbudujBut(materialy);
  os.position.x = PIETA_X;
  but.position.x = -PIETA_X;
  os.scale.setScalar(skalaRozmiaru(stan0.rozmiary));
  os.add(but);
  skok.add(os);
  obrot.add(skok);
  const miarka = utworzMiarke(katalog.rozmiary);
  miarka.rysuj(stan0.rozmiary);
  obrot.add(miarka.siatka);
  scena.add(obrot);
  const wezly = utworzWezly();
  scena.add(wezly.grupa);

  const kierunek = new THREE.Vector3(...UJECIA.hero.kierunek).normalize();
  const cel = new THREE.Vector3(...UJECIA.hero.cel);
  const kadr = { wartosc: UJECIA.hero.kadr };
  const ruch = { obrot: UJECIA.hero.obrot, krecenie: 0, przewiniecie: 0, przewiniecieCel: 0, nachylenieX: 0, nachylenieY: 0, wskaznikX: 0, wskaznikY: 0 };
  let ujecie = "hero";
  let widoczna = true;
  let doNarysowania = KLATKI_PO_ZMIANIE;
  const obudz = () => {
    doNarysowania = KLATKI_PO_ZMIANIE;
  };

  function celUjecia(nazwa) {
    const u = UJECIA[nazwa];
    if (nazwa !== "rozmiar") return u.cel;
    const { rozmiary } = pobierz();
    const najwiekszy = rozmiary.length ? Math.max(...rozmiary.map(Number)) : 42;
    return [pozycjaRozmiaru(najwiekszy) - 0.2, u.cel[1], u.cel[2]];
  }

  function ustawUjecie(nazwa) {
    const u = UJECIA[nazwa];
    if (!u || nazwa === ujecie) return;
    const poprzednie = UJECIA[ujecie];
    ujecie = nazwa;
    obudz();
    const docelowyCel = celUjecia(nazwa);
    const docelowy = new THREE.Vector3(...u.kierunek).normalize();
    gsap.to(kierunek, { x: docelowy.x, y: docelowy.y, z: docelowy.z, duration: 1.6, ease: "power3.inOut", overwrite: true });
    gsap.to(cel, { x: docelowyCel[0], y: docelowyCel[1], z: docelowyCel[2], duration: 1.6, ease: "power3.inOut", overwrite: true });
    gsap.to(kadr, { wartosc: u.kadr, duration: 1.6, ease: "power3.inOut", overwrite: true });
    gsap.to(ruch, { obrot: u.obrot, duration: 1.6, ease: "power3.inOut", overwrite: "auto" });
    if (poprzednie.krecenie && !u.krecenie) {
      gsap.to(ruch, { krecenie: Math.round(ruch.krecenie / PELNY_OBROT) * PELNY_OBROT, duration: 1.6, ease: "power3.inOut" });
    }
    gsap.to(miarka.siatka.material, { opacity: u.miarka ? 1 : 0, duration: u.miarka ? 0.8 : 0.35, delay: u.miarka ? 0.5 : 0 });
  }

  function zmienMarke(marka) {
    const z = zestaw(marka);
    for (const klucz of CZESCI) {
      const docelowy = new THREE.Color(z[klucz]);
      gsap.to(materialy[klucz].color, { r: docelowy.r, g: docelowy.g, b: docelowy.b, duration: 0.7, ease: "power2.inOut" });
    }
    gsap.to(materialy.cholewka, { roughness: z.szorstkosc, sheen: z.polysk, duration: 0.7 });
    gsap
      .timeline()
      .to(skok.position, { y: 0.45, duration: 0.4, ease: "power2.out" })
      .to(skok.rotation, { y: `+=${PELNY_OBROT}`, duration: 0.8, ease: "power3.inOut" }, 0)
      .to(skok.position, { y: 0, duration: 0.55, ease: "bounce.out" }, 0.4)
      .add(() => {
        skok.rotation.y %= PELNY_OBROT;
      });
  }

  function zmienModel() {
    gsap.fromTo(skok.rotation, { z: 0.09 }, { z: 0, duration: 1, ease: "elastic.out(1, 0.35)" });
  }

  let prawdziwy = null;
  let zadanyAdres = null;

  function adresModelu3d(stan) {
    const marka = katalog.marki.find((m) => m.id === stan.marka);
    return marka?.modele.find((m) => m.id === stan.model)?.model3d || null;
  }

  function pokaz(obiekt, widoczny) {
    gsap.killTweensOf(obiekt.scale);
    if (widoczny) {
      obiekt.visible = true;
      gsap.fromTo(obiekt.scale, { x: 0.001, y: 0.001, z: 0.001 }, { x: 1, y: 1, z: 1, duration: 0.6, ease: "back.out(1.8)", onUpdate: obudz });
      return;
    }
    gsap.to(obiekt.scale, { x: 0.001, y: 0.001, z: 0.001, duration: 0.3, ease: "power2.in", onUpdate: obudz, onComplete: () => (obiekt.visible = false) });
  }

  function pokazStylizowany() {
    if (prawdziwy?.visible) pokaz(prawdziwy, false);
    if (!but.visible || but.scale.x < 1) pokaz(but, true);
    kontener.dataset.model3d = "stylizowany";
  }

  async function ustawPrawdziwy(adres) {
    zadanyAdres = adres;
    if (!adres) {
      pokazStylizowany();
      return;
    }
    kontener.dataset.model3d = "ladowanie";
    try {
      const obiekt = await wczytajPrawdziwy(adres);
      if (zadanyAdres !== adres) return;
      if (prawdziwy && prawdziwy !== obiekt) {
        gsap.killTweensOf(prawdziwy.scale);
        os.remove(prawdziwy);
      }
      prawdziwy = obiekt;
      if (!obiekt.parent) os.add(obiekt);
      if (but.visible) pokaz(but, false);
      pokaz(obiekt, true);
      kontener.dataset.model3d = "prawdziwy";
    } catch {
      if (zadanyAdres === adres) pokazStylizowany();
    }
  }

  function zmienRozmiar(rozmiary) {
    gsap.to(os.scale, { x: skalaRozmiaru(rozmiary), y: skalaRozmiaru(rozmiary), z: skalaRozmiaru(rozmiary), duration: 0.7, ease: "back.out(2)" });
    miarka.rysuj(rozmiary);
    if (ujecie === "rozmiar") gsap.to(cel, { x: celUjecia("rozmiar")[0], duration: 0.8, ease: "power3.out", overwrite: "auto" });
  }

  subskrybuj((stan, poprzedni) => {
    obudz();
    if (stan.marka !== poprzedni.marka) zmienMarke(stan.marka);
    else if (stan.model !== poprzedni.model && stan.model) zmienModel();
    if (stan.marka !== poprzedni.marka || stan.model !== poprzedni.model) ustawPrawdziwy(adresModelu3d(stan));
    if (stan.rozmiary !== poprzedni.rozmiary) zmienRozmiar(stan.rozmiary);
  });

  document.addEventListener("szatnia:wyszukiwanie", ({ detail: { typ, dane } }) => {
    obudz();
    if (typ === "start") wezly.ustaw(dane.zrodla);
    else if (typ === "zrodlo_start") wezly.stan(dane.zrodlo, "trwa");
    else if (typ === "zrodlo_koniec") wezly.stan(dane.nazwa, dane.status, dane.ofert);
  });

  for (const sekcja of document.querySelectorAll(".hero, .krok, .postep")) {
    ScrollTrigger.create({
      trigger: sekcja,
      start: "top 55%",
      end: "bottom 55%",
      onToggle: (wyzwalacz) => wyzwalacz.isActive && ustawUjecie(nazwaUjecia(sekcja)),
    });
  }
  ScrollTrigger.create({
    start: 0,
    end: "max",
    onUpdate: (wyzwalacz) => {
      ruch.przewiniecieCel = (wyzwalacz.progress - 0.5) * 0.7;
      obudz();
    },
  });

  if (window.matchMedia("(pointer: fine)").matches) {
    window.addEventListener("pointermove", (zdarzenie) => {
      ruch.wskaznikX = (zdarzenie.clientX / window.innerWidth - 0.5) * 2;
      ruch.wskaznikY = (zdarzenie.clientY / window.innerHeight - 0.5) * 2;
      obudz();
    });
  }

  new IntersectionObserver(([wpis]) => {
    widoczna = wpis.isIntersecting;
  }).observe(kontener);

  function dopasujRozmiar() {
    const { width, height } = kontener.getBoundingClientRect();
    if (!width || !height) return;
    renderer.setSize(width, height, false);
    kamera.aspect = width / height;
    kamera.updateProjectionMatrix();
    obudz();
  }
  new ResizeObserver(dopasujRozmiar).observe(kontener);
  dopasujRozmiar();

  gsap.ticker.add((_czas, delta) => {
    if (!widoczna) return;
    if (!UJECIA[ujecie].krecenie && !wezly.aktywne && doNarysowania <= 0) return;
    doNarysowania -= 1;
    const dt = Math.min(delta, 50) / 1000;
    wezly.aktualizuj(dt);
    if (UJECIA[ujecie].krecenie) ruch.krecenie += dt * 0.22;
    const wygladzenie = 1 - Math.exp(-dt * 4);
    ruch.przewiniecie += (ruch.przewiniecieCel - ruch.przewiniecie) * wygladzenie;
    ruch.nachylenieX += (ruch.wskaznikY * 0.05 - ruch.nachylenieX) * wygladzenie;
    ruch.nachylenieY += (ruch.wskaznikX * 0.14 - ruch.nachylenieY) * wygladzenie;
    obrot.rotation.y = ruch.obrot + ruch.krecenie + ruch.przewiniecie + ruch.nachylenieY;
    obrot.rotation.x = ruch.nachylenieX;
    const polowaPionowa = THREE.MathUtils.degToRad(kamera.fov / 2);
    const polowaPozioma = Math.atan(Math.tan(polowaPionowa) * kamera.aspect);
    const odleglosc = (kadr.wartosc * PROMIEN_BUTA * os.scale.x) / Math.sin(Math.min(polowaPionowa, polowaPozioma));
    kamera.position.copy(kierunek).normalize().multiplyScalar(odleglosc).add(cel);
    kamera.lookAt(cel);
    renderer.render(scena, kamera);
  });

  kontener.dataset.tryb = "3d";
  kontener.dataset.model3d = "stylizowany";
  ustawPrawdziwy(adresModelu3d(stan0));
  gsap.fromTo(renderer.domElement, { opacity: 0 }, { opacity: 1, duration: 1.2, ease: "power2.out" });
  return { ustawUjecie };
}
