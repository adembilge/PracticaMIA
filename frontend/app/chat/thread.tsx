"use client"

import { useEffect, useState, type FormEvent } from "react"
import { loadCase } from "../../lib/case"
import { copy, type Lang } from "../../lib/copy"
import { loadThread, sendLine } from "../../lib/thread"
import { Warning } from "../shell"

export function Thread({ lang }: { lang: Lang }) {
  const text = copy[lang]
  const [view, setView] = useState<"loading" | "empty" | "error" | "thread">("loading")
  const [caseId, setCaseId] = useState("")
  const [messages, setMessages] = useState<string[]>([])
  const [question, setQuestion] = useState<string | null>(null)
  const [draft, setDraft] = useState("")
  const [pending, setPending] = useState(false)
  const [warning, setWarning] = useState("")

  useEffect(() => {
    let current = true
    loadCase().then((result) => {
      if (!current) return
      if ("error" in result) {
        setView("error")
        return
      }
      if ("empty" in result) {
        setView("empty")
        return
      }
      loadThread(result.id).then((thread) => {
        if (!current) return
        if ("error" in thread) {
          setView("error")
          return
        }
        setCaseId(result.id)
        setMessages(thread.messages)
        setQuestion(thread.question)
        setView("thread")
      })
    })
    return () => {
      current = false
    }
  }, [])

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    const next = draft.trim()
    if (!next || pending) return
    setPending(true)
    setWarning("")
    try {
      const result = await sendLine(caseId, next)
      if ("error" in result) {
        setPending(false)
        setWarning(text.error)
        return
      }
      setDraft("")
      setMessages(result.messages)
      setQuestion(result.question)
      setWarning(result.text || "")
      setPending(false)
    } catch {
      setPending(false)
      setWarning(text.error)
    }
  }

  if (view === "loading") return <p className="status">{text.loading}</p>
  if (view === "empty") return <Warning text={text.none} />
  if (view === "error") return <Warning text={text.error} />
  return (
    <div className="block">
      {messages.map((line, index) => <p key={index}>{line}</p>)}
      {question ? (
        <form onSubmit={onSubmit}>
          <label>
            {question}
            <textarea value={draft} onChange={(event) => setDraft(event.target.value)} />
          </label>
          <button type="submit">{pending ? text.loading : text.continue}</button>
        </form>
      ) : null}
      {warning ? <Warning text={warning} /> : null}
    </div>
  )
}
