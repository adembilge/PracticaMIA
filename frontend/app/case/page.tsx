import { copy } from "../../lib/copy"
import { CaseShell, StatusLine } from "../shell"

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ lang?: string }>
}) {
  const params = await searchParams
  const lang = params.lang === "it" ? "it" : "en"
  return (
    <CaseShell lang={lang} path="/case">
      <StatusLine word={copy[lang].notReady} role="not-ready" />
    </CaseShell>
  )
}
