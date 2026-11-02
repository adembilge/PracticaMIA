import { copy } from "../lib/copy"
import { Language } from "./shell"
import { StartButton } from "./start-button"

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ lang?: string }>
}) {
  const params = await searchParams
  const lang = params.lang === "it" ? "it" : "en"
  const text = copy[lang]
  return (
    <main id="content" lang={lang}>
      <Language path="/" />
      <p className="status">{text.none}</p>
      <StartButton label={text.continue} loading={text.loading} error={text.error} />
    </main>
  )
}
