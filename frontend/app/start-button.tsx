"use client"

import { useState } from "react"
import { startPerson } from "../lib/start"
import { Warning } from "./shell"

export function StartButton({
  label,
  loading,
  error,
}: {
  label: string
  loading: string
  error: string
}) {
  const [pending, setPending] = useState(false)
  const [message, setMessage] = useState("")

  async function onClick() {
    setPending(true)
    setMessage("")
    try {
      const result = await startPerson()
      setPending(false)
      if ("error" in result) setMessage(error)
    } catch {
      setPending(false)
      setMessage(error)
    }
  }

  return (
    <div>
      <button type="button" onClick={onClick}>{pending ? loading : label}</button>
      {message ? <Warning text={message} /> : null}
    </div>
  )
}
