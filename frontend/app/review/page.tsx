import { CaseShell } from "../shell"
import { Review } from "./view"

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ lang?: string }>
}) {
  const params = await searchParams
  const lang = params.lang === "it" ? "it" : "en"
  return (
    <CaseShell lang={lang} path="/review">
      <Review lang={lang} />
    </CaseShell>
  )
}
