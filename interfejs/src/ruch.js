import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Lenis from "lenis";

gsap.registerPlugin(ScrollTrigger);

const ZAPYTANIE_RUCHU = window.matchMedia("(prefers-reduced-motion: reduce)");
let lenis = null;

export function ograniczonyRuch() {
  return ZAPYTANIE_RUCHU.matches;
}

export function uruchomPrzewijanie() {
  if (ograniczonyRuch()) {
    document.documentElement.dataset.ruch = "ograniczony";
    return;
  }
  lenis = new Lenis({ lerp: 0.1, wheelMultiplier: 1, touchMultiplier: 1.4 });
  lenis.on("scroll", ScrollTrigger.update);
  gsap.ticker.add((czas) => lenis.raf(czas * 1000));
  gsap.ticker.lagSmoothing(0);
  document.documentElement.dataset.ruch = "pelny";
}

export function przewin(cel, { skupienie = true } = {}) {
  const element = typeof cel === "string" ? document.querySelector(cel) : cel;
  if (!element) return;
  const poPrzewinieciu = () => {
    if (!skupienie) return;
    const naglowek = element.querySelector("h2") || element;
    if (!naglowek.hasAttribute("tabindex")) naglowek.setAttribute("tabindex", "-1");
    naglowek.focus({ preventScroll: true });
  };
  if (lenis) {
    lenis.scrollTo(element, { duration: 1.1, onComplete: poPrzewinieciu });
  } else {
    element.scrollIntoView({ block: "start" });
    poPrzewinieciu();
  }
}

export function podepnijKotwice() {
  document.addEventListener("click", (zdarzenie) => {
    const link = zdarzenie.target.closest('a[href^="#"]');
    if (!link || link.getAttribute("href") === "#") return;
    const cel = document.querySelector(link.getAttribute("href"));
    if (!cel) return;
    zdarzenie.preventDefault();
    history.replaceState(null, "", `${location.pathname}${location.search}${link.getAttribute("href")}`);
    przewin(cel, { skupienie: link.getAttribute("href") !== "#start" });
  });
}

export function wejscieHero() {
  if (ograniczonyRuch()) return;
  const os = gsap.timeline({ defaults: { ease: "power3.out" } });
  os.from(".hero > *", { y: 28, opacity: 0, duration: 0.8, stagger: 0.08 })
    .from(".scena__but", { x: 80, opacity: 0, rotate: -4, duration: 1.2, ease: "expo.out" }, 0.1)
    .from(".scena__swiatlo", { scale: 0.7, opacity: 0, duration: 1.4 }, 0);
}

export function odslonyKrokow() {
  if (ograniczonyRuch()) return;
  for (const sekcja of document.querySelectorAll(".krok")) {
    gsap.from(sekcja.querySelectorAll(":scope > :not(.krok__dalej)"), {
      y: 24,
      opacity: 0,
      duration: 0.6,
      stagger: 0.07,
      ease: "power2.out",
      clearProps: "opacity,transform,translate",
      scrollTrigger: { trigger: sekcja, start: "top 78%", toggleActions: "play none none reverse" },
    });
  }
}

export function sledzKroki(naZmiane) {
  for (const sekcja of document.querySelectorAll(".krok")) {
    ScrollTrigger.create({
      trigger: sekcja,
      start: "top 55%",
      end: "bottom 55%",
      onToggle: (wyzwalacz) => naZmiane(sekcja.dataset.krok, wyzwalacz.isActive),
    });
  }
}

export function sledzHero(naZmiane) {
  ScrollTrigger.create({
    trigger: ".hero",
    start: "bottom 70%",
    onEnter: () => naZmiane(false),
    onLeaveBack: () => naZmiane(true),
  });
}

export function sprezyna(element) {
  if (ograniczonyRuch() || !element) return;
  gsap.fromTo(element, { scale: 0.96 }, { scale: 1, duration: 0.5, ease: "back.out(3)", clearProps: "transform" });
}

export function pojawienie(elementy) {
  if (ograniczonyRuch() || !elementy.length) return;
  gsap.from(elementy, { y: 12, opacity: 0, duration: 0.4, stagger: 0.04, ease: "power2.out", clearProps: "all" });
}

export function wstrzymajPrzewijanie(wstrzymaj) {
  if (!lenis) return;
  if (wstrzymaj) lenis.stop();
  else lenis.start();
}

export function odswiezWyzwalacze() {
  ScrollTrigger.refresh();
}
