import { Papers } from "./papers"
import { CaseShell } from "../shell"

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ lang?: string }>
}) {
  const params = await searchParams
  const lang = params.lang === "it" ? "it" : "en"
  return (
    <CaseShell lang={lang} path="/documents">
      <Papers lang={lang} />
    </CaseShell>
  )
}
