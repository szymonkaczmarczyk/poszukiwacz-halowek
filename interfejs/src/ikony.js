import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  Check,
  CircleAlert,
  CircleCheck,
  CircleX,
  Clock,
  ExternalLink,
  LoaderCircle,
  Pause,
  RefreshCw,
  Search,
  Square,
  Plus,
  Trash2,
  X,
  EyeOff,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Minus,
  TriangleAlert,
  createElement,
} from "lucide";

const IKONY = {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  Check,
  CircleAlert,
  CircleCheck,
  CircleX,
  Clock,
  ExternalLink,
  LoaderCircle,
  Pause,
  RefreshCw,
  Search,
  Square,
  Plus,
  Trash2,
  X,
  EyeOff,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Minus,
  TriangleAlert,
};

export function ikona(nazwa) {
  const svg = createElement(IKONY[nazwa]);
  svg.classList.add("lucide");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  return svg;
}

export function wstawIkony(korzen = document) {
  for (const miejsce of korzen.querySelectorAll("[data-ikona]")) {
    miejsce.replaceWith(ikona(miejsce.dataset.ikona));
  }
}
