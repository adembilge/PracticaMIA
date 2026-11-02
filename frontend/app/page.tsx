import { Dashboard } from "./dashboard"

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ lang?: string }>
}) {
  const params = await searchParams
  const lang = params.lang === "it" ? "it" : "en"
  return <Dashboard lang={lang} />
}
