export type Lang = "en" | "it"

export const copy = {
  en: {
    case: "Case",
    chat: "Chat",
    documents: "Documents",
    checklist: "Checklist",
    review: "Review",
    none: "No open case",
    notReady: "not ready",
    ready: "ready to hand over",
    continue: "Continue",
    loading: "Loading",
    error: "Error.",
  },
  it: {
    case: "Caso",
    chat: "Chat",
    documents: "Documenti",
    checklist: "Elenco",
    review: "Revisione",
    none: "Nessun caso aperto",
    notReady: "not ready",
    ready: "ready to hand over",
    continue: "Continua",
    loading: "Caricamento",
    error: "Error.",
  },
} as const
