import { copy, type Lang } from "../lib/copy"
import { CaseShell, StatusLine } from "./shell"

export function OpenCase({
  lang,
  stop,
}: {
  lang: Lang
  stop: "not ready" | "ready to hand over"
}) {
  const text = copy[lang]
  const query = lang === "it" ? "?lang=it" : ""
  const ready = stop === "ready to hand over"
  return (
    <CaseShell lang={lang} path="/">
      <StatusLine word={ready ? text.ready : text.notReady} role={ready ? "ready" : "not-ready"} />
      <a href={"/case" + query}>{text.continue}</a>
    </CaseShell>
  )
}
