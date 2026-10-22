import * as THREE from "three";

export const CZESCI = ["cholewka", "nosek", "zapietek", "pas", "podeszwa", "sznurowki"];

export const ZESTAWY = {
  domyslny: { cholewka: "#3a3b41", nosek: "#33343a", zapietek: "#2e2f35", pas: "#6e95ff", podeszwa: "#2a2b30", sznurowki: "#8a8c95", szorstkosc: 0.6, polysk: 0.2 },
  munich: { cholewka: "#efede6", nosek: "#e7e4db", zapietek: "#1d2b4f", pas: "#1d2b4f", podeszwa: "#c48647", sznurowki: "#f4f2ec", szorstkosc: 0.42, polysk: 0.1 },
  joma: { cholewka: "#203062", nosek: "#1a2850", zapietek: "#eeede8", pas: "#eeede8", podeszwa: "#b77a40", sznurowki: "#eeede8", szorstkosc: 0.8, polysk: 0.25 },
  nike: { cholewka: "#18181b", nosek: "#202024", zapietek: "#18181b", pas: "#d9e44a", podeszwa: "#a8743f", sznurowki: "#ecece6", szorstkosc: 0.5, polysk: 0.2 },
  adidas: { cholewka: "#f2f1ec", nosek: "#e8e6df", zapietek: "#141416", pas: "#141416", podeszwa: "#c08a52", sznurowki: "#f6f5f0", szorstkosc: 0.45, polysk: 0.1 },
  mizuno: { cholewka: "#1f4fb8", nosek: "#1a45a3", zapietek: "#f3f3ef", pas: "#f3f3ef", podeszwa: "#ecebe6", sznurowki: "#f3f3ef", szorstkosc: 0.4, polysk: 0.1 },
  ortuseight: { cholewka: "#ece5d3", nosek: "#e2dac6", zapietek: "#55553f", pas: "#d23a2c", podeszwa: "#b98552", sznurowki: "#f2eee4", szorstkosc: 0.45, polysk: 0.12 },
};

export function zestaw(marka) {
  return ZESTAWY[marka] || ZESTAWY.domyslny;
}

export function utworzMaterialy(poczatkowy) {
  const z = zestaw(poczatkowy);
  const lakier = { roughness: 0.4, clearcoat: 0.3, clearcoatRoughness: 0.4 };
  return {
    cholewka: new THREE.MeshPhysicalMaterial({ color: z.cholewka, vertexColors: true, roughness: z.szorstkosc, sheen: z.polysk, sheenRoughness: 0.8, sheenColor: new THREE.Color("#ffffff"), clearcoat: 0.12, clearcoatRoughness: 0.6, side: THREE.DoubleSide }),
    nosek: new THREE.MeshPhysicalMaterial({ color: z.nosek, ...lakier }),
    zapietek: new THREE.MeshPhysicalMaterial({ color: z.zapietek, ...lakier }),
    pas: new THREE.MeshPhysicalMaterial({ color: z.pas, ...lakier }),
    podeszwa: new THREE.MeshPhysicalMaterial({ color: z.podeszwa, roughness: 0.32, clearcoat: 0.5, clearcoatRoughness: 0.25 }),
    sznurowki: new THREE.MeshStandardMaterial({ color: z.sznurowki, roughness: 0.9 }),
  };
}
