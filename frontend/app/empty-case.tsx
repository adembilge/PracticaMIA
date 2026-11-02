"use client"

import { useState, type FormEvent } from "react"
import { beginCase } from "../lib/begin"
import { copy, type Lang } from "../lib/copy"
import { Language, Warning } from "./shell"

const OPENING =
  "This release handles one adult changing address inside Milan. You submit the declaration yourself."

export function EmptyCase({ lang }: { lang: Lang }) {
  const text = copy[lang]
  const [messages, setMessages] = useState<string[]>([])
  const [label, setLabel] = useState(OPENING)
  const [draft, setDraft] = useState("")
  const [pending, setPending] = useState(false)
  const [warning, setWarning] = useState("")

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    const next = draft.trim()
    if (!next || pending) return
    const sent = messages.concat(next)
    setPending(true)
    setWarning("")
    try {
      const result = await beginCase(sent)
      if ("error" in result) {
        setPending(false)
        setWarning(text.error)
        return
      }
      if ("case" in result) {
        window.location.assign(lang === "it" ? "/?lang=it" : "/")
        return
      }
      setMessages(sent)
      setDraft("")
      setLabel(result.text)
      setPending(false)
    } catch {
      setPending(false)
      setWarning(text.error)
    }
  }

  return (
    <main id="content" lang={lang}>
      <Language path="/" />
      <p className="status">{text.none}</p>
      <form onSubmit={onSubmit}>
        <label>
          {label}
          <textarea value={draft} onChange={(event) => setDraft(event.target.value)} />
        </label>
        <button type="submit">{pending ? text.loading : text.continue}</button>
      </form>
      {warning ? <Warning text={warning} /> : null}
    </main>
  )
}
