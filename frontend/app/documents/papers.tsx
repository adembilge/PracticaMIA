"use client"

import { useEffect, useState, type FormEvent } from "react"
import { loadCase } from "../../lib/case"
import { copy, type Lang } from "../../lib/copy"
import { loadPapers, sendPaper, type Papers } from "../../lib/papers"
import { StatusLine, Warning } from "../shell"

const FAILED = "The file did not upload."
const UNREADABLE = "The file cannot be read."

function titleLabel(f05: string | null) {
  if (f05 === "Owner") return "Please upload the ownership paper."
  if (f05 === "named tenant") return "Please upload the lease."
  return "Please upload the lease or the ownership paper. Your name must be on it."
}

function problem(uploads: Papers["uploads"], forced: boolean) {
  if (forced || uploads.some((item) => item.status === "failed")) return FAILED
  if (uploads.some((item) => item.status === "unreadable")) return UNREADABLE
  return ""
}

export function Papers({ lang }: { lang: Lang }) {
  const text = copy[lang]
  const [view, setView] = useState<"loading" | "empty" | "error" | "papers">("loading")
  const [caseId, setCaseId] = useState("")
  const [papers, setPapers] = useState<Papers | null>(null)
  const [pending, setPending] = useState<"" | "title" | "identity">("")
  const [warning, setWarning] = useState("")

  function apply(next: Papers) {
    setPapers(next)
    setWarning(problem(next.uploads, false))
    setView("papers")
  }

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
      loadPapers(result.id).then((loaded) => {
        if (!current) return
        if ("error" in loaded) {
          setView("error")
          return
        }
        setCaseId(result.id)
        apply(loaded)
      })
    })
    return () => {
      current = false
    }
  }, [])

  async function onSubmit(role: "title" | "identity", event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const input = form.elements.namedItem("file")
    if (!(input instanceof HTMLInputElement) || !input.files || !input.files[0] || pending) return
    const file = input.files[0]
    setPending(role)
    try {
      const result = await sendPaper(caseId, role, file)
      if ("error" in result) {
        setPending("")
        setWarning(text.error)
        return
      }
      const loaded = await loadPapers(caseId)
      if ("error" in loaded) {
        setPending("")
        setWarning(text.error)
        return
      }
      form.reset()
      setPapers(loaded)
      setWarning(problem(loaded.uploads, "failed" in result))
      setPending("")
    } catch {
      setPending("")
      setWarning(text.error)
    }
  }

  if (view === "loading") return <p className="status">{text.loading}</p>
  if (view === "empty") return <Warning text={text.none} />
  if (view === "error" || !papers) return <Warning text={text.error} />
  const ready = papers.stop === "ready to hand over"
  const roles: Array<"title" | "identity"> = papers.f06 === "Yes" ? ["title", "identity"] : ["title"]
  return (
    <div className="block">
      <StatusLine word={ready ? text.ready : text.notReady} role={ready ? "ready" : "not-ready"} />
      {roles.map((role) => {
        const found = papers.uploads.find((item) => item.role === role)
        const label = role === "title" ? titleLabel(papers.f05) : "permesso di soggiorno"
        return (
          <form key={role} onSubmit={(event) => onSubmit(role, event)}>
            <label>
              {label}
              <input name="file" type="file" />
            </label>
            {found ? <p className="status">{found.status}</p> : null}
            <button type="submit">{pending === role ? text.loading : text.continue}</button>
          </form>
        )
      })}
      {warning ? <Warning text={warning} /> : null}
    </div>
  )
}
