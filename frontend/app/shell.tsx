import { copy, type Lang } from "../lib/copy"

const ROUTES = [
  ["case", "/case"],
  ["chat", "/chat"],
  ["documents", "/documents"],
  ["checklist", "/checklist"],
  ["review", "/review"],
] as const

export function Language({ path }: { path: string }) {
  return (
    <p className="languages">
      <a href={path}>English</a>
      <a href={path + "?lang=it"}>Italian</a>
    </p>
  )
}

export function StatusLine({ word, role }: { word: string, role: "not-ready" | "ready" | "blocked" }) {
  return <p className={"status status-" + role}>{word}</p>
}

export function Warning({ text }: { text: string }) {
  return <p className="warning" role="alert">{text}</p>
}

export function CaseShell({
  lang,
  path,
  children,
}: {
  lang: Lang
  path: string
  children: React.ReactNode
}) {
  const text = copy[lang]
  const query = lang === "it" ? "?lang=it" : ""
  return (
    <main id="content" lang={lang} className="shell">
      <nav className="routes">
        {ROUTES.map(([key, href]) => (
          <a key={href} href={href + query}>{text[key]}</a>
        ))}
      </nav>
      <section>
        <Language path={path} />
        {children}
      </section>
    </main>
  )
}
