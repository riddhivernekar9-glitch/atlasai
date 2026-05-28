'use client'

import { useEffect, useRef, useState, FormEvent, KeyboardEvent } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase'
import {
  answerQuery,
  ingestPath,
  healthCheck,
  ChatMessage,
  SearchResult,
} from '@/lib/api'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: SearchResult[]
  structured?: Record<string, string>
  confidence?: Record<string, string>
  error?: boolean
}

type IngestStatus =
  | { state: 'idle' }
  | { state: 'loading' }
  | { state: 'success'; count: number; chunks: number; folder: string }
  | { state: 'error'; message: string }

// ---------------------------------------------------------------------------
// Small UI helpers
// ---------------------------------------------------------------------------

function Spinner({ className = '' }: { className?: string }) {
  return (
    <svg
      className={`animate-spin ${className}`}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
      />
    </svg>
  )
}

function ConfidenceBadge({ label }: { label: string }) {
  const colours: Record<string, string> = {
    High: 'bg-emerald-100 text-emerald-700',
    Medium: 'bg-amber-100 text-amber-700',
    Low: 'bg-red-100 text-red-700',
  }
  return (
    <span
      className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${colours[label] ?? 'bg-zinc-100 text-zinc-600'}`}
    >
      {label}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Chat panel
// ---------------------------------------------------------------------------

function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function sendMessage() {
    const text = input.trim()
    if (!text || loading) return

    const userMsg: Message = { role: 'user', content: text }
    const nextMessages = [...messages, userMsg]
    setMessages(nextMessages)
    setInput('')
    setLoading(true)

    // Build history for multi-turn (exclude the message just added)
    const history: ChatMessage[] = messages.map((m) => ({
      role: m.role,
      content: m.content,
    }))

    try {
      const data = await answerQuery(text, history)
      const assistantMsg: Message = {
        role: 'assistant',
        content: data.answer,
        sources: data.sources,
        structured: data.structured,
        confidence: data.confidence,
      }
      setMessages([...nextMessages, assistantMsg])
    } catch (err) {
      setMessages([
        ...nextMessages,
        {
          role: 'assistant',
          content:
            err instanceof Error
              ? `Error: ${err.message}`
              : 'An unexpected error occurred. Is the backend running?',
          error: true,
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex-none px-4 py-3 border-b border-zinc-200 bg-white">
        <h2 className="text-sm font-semibold text-zinc-700 uppercase tracking-wider">
          Chat
        </h2>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 bg-zinc-50">
        {messages.length === 0 && (
          <p className="text-center text-sm text-zinc-400 mt-12">
            Ask a question about your documents…
          </p>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm ${
                msg.role === 'user'
                  ? 'bg-indigo-600 text-white rounded-br-sm'
                  : msg.error
                  ? 'bg-red-50 text-red-700 border border-red-200 rounded-bl-sm'
                  : 'bg-white text-zinc-800 border border-zinc-200 rounded-bl-sm'
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>

              {/* Structured fields */}
              {msg.structured && Object.keys(msg.structured).length > 0 && (
                <div className="mt-3 pt-3 border-t border-zinc-100 space-y-1.5">
                  {Object.entries(msg.structured).map(([field, value]) => (
                    <div key={field} className="flex items-start gap-2 text-xs">
                      <span className="font-semibold text-zinc-500 min-w-[70px]">
                        {field}
                      </span>
                      <span className="text-zinc-700 flex-1">{value}</span>
                      {msg.confidence?.[field] && (
                        <ConfidenceBadge label={msg.confidence[field]} />
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Sources */}
              {msg.sources && msg.sources.length > 0 && (
                <details className="mt-3">
                  <summary className="cursor-pointer text-xs text-zinc-400 hover:text-zinc-600 select-none">
                    {msg.sources.length} source
                    {msg.sources.length !== 1 ? 's' : ''}
                  </summary>
                  <ul className="mt-2 space-y-2">
                    {msg.sources.map((src, j) => (
                      <li
                        key={j}
                        className="rounded-lg bg-zinc-50 border border-zinc-100 p-2 text-xs"
                      >
                        <div className="flex items-center justify-between gap-2 mb-1">
                          <span className="font-medium text-zinc-600 truncate">
                            {src.relative_path}
                          </span>
                          <span className="flex-none text-zinc-400">
                            {(src.score * 100).toFixed(0)}%
                          </span>
                        </div>
                        <p className="text-zinc-500 line-clamp-2">{src.context}</p>
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-zinc-200 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
              <div className="flex gap-1.5 items-center">
                <span className="h-2 w-2 bg-indigo-400 rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="h-2 w-2 bg-indigo-400 rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="h-2 w-2 bg-indigo-400 rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="flex-none px-4 py-3 border-t border-zinc-200 bg-white">
        <div className="flex gap-2 items-end">
          <textarea
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question… (Enter to send, Shift+Enter for newline)"
            disabled={loading}
            className="flex-1 resize-none rounded-xl border border-zinc-300 bg-zinc-50 px-3 py-2 text-sm text-zinc-900 placeholder-zinc-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 disabled:opacity-50 max-h-32 overflow-y-auto"
            style={{ fieldSizing: 'content' } as React.CSSProperties}
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="flex-none h-9 w-9 rounded-xl bg-indigo-600 text-white flex items-center justify-center shadow-sm transition-colors hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Send message"
          >
            {loading ? (
              <Spinner className="h-4 w-4 text-white" />
            ) : (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="h-4 w-4"
              >
                <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
              </svg>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Ingest panel
// ---------------------------------------------------------------------------

function IngestPanel() {
  const [path, setPath] = useState('')
  const [status, setStatus] = useState<IngestStatus>({ state: 'idle' })

  async function handleIngest(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const trimmed = path.trim()
    if (!trimmed) return

    setStatus({ state: 'loading' })
    try {
      const result = await ingestPath(trimmed)
      if (result.ok) {
        setStatus({
          state: 'success',
          count: result.count ?? 0,
          chunks: result.chunks ?? 0,
          folder: result.folder ?? trimmed,
        })
      } else {
        setStatus({
          state: 'error',
          message: result.error ?? 'Ingest failed for an unknown reason.',
        })
      }
    } catch (err) {
      setStatus({
        state: 'error',
        message:
          err instanceof Error
            ? err.message
            : 'Network error — is the backend running?',
      })
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex-none px-4 py-3 border-b border-zinc-200 bg-white">
        <h2 className="text-sm font-semibold text-zinc-700 uppercase tracking-wider">
          Ingest
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-6 bg-zinc-50 space-y-6">
        {/* Form */}
        <div className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm">
          <p className="mb-4 text-sm text-zinc-600">
            Enter the path to a folder (or single file) on this machine to index
            it for semantic search.
          </p>
          <form onSubmit={handleIngest} className="space-y-3">
            <div>
              <label
                htmlFor="ingest-path"
                className="mb-1.5 block text-sm font-medium text-zinc-700"
              >
                Folder / file path
              </label>
              <input
                id="ingest-path"
                type="text"
                value={path}
                onChange={(e) => setPath(e.target.value)}
                placeholder="/Users/you/Documents/HR"
                required
                disabled={status.state === 'loading'}
                className="w-full rounded-lg border border-zinc-300 bg-zinc-50 px-3 py-2 text-sm font-mono text-zinc-900 placeholder-zinc-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 disabled:opacity-50"
              />
            </div>
            <button
              type="submit"
              disabled={status.state === 'loading' || !path.trim()}
              className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {status.state === 'loading' && (
                <Spinner className="h-4 w-4 text-white" />
              )}
              {status.state === 'loading' ? 'Indexing…' : 'Ingest'}
            </button>
          </form>
        </div>

        {/* Result */}
        {status.state === 'success' && (
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5 space-y-3">
            <div className="flex items-center gap-2">
              <svg
                className="h-5 w-5 text-emerald-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M5 13l4 4L19 7"
                />
              </svg>
              <span className="text-sm font-semibold text-emerald-800">
                Indexed successfully
              </span>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Stat label="Files" value={status.count} />
              <Stat label="Chunks" value={status.chunks} />
            </div>
            <p className="text-xs text-emerald-700 font-mono truncate">
              {status.folder}
            </p>
          </div>
        )}

        {status.state === 'error' && (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-5">
            <div className="flex items-center gap-2 mb-2">
              <svg
                className="h-5 w-5 text-red-500"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
              <span className="text-sm font-semibold text-red-700">
                Ingest failed
              </span>
            </div>
            <p className="text-sm text-red-600">{status.message}</p>
          </div>
        )}

        {/* Tips */}
        <div className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-3">
            Supported formats
          </h3>
          <div className="flex flex-wrap gap-2">
            {['.pdf', '.txt', '.md', '.docx', '.xlsx', '.pptx', '.html'].map(
              (ext) => (
                <span
                  key={ext}
                  className="rounded-md bg-zinc-100 px-2 py-1 text-xs font-mono text-zinc-600"
                >
                  {ext}
                </span>
              ),
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl bg-white border border-emerald-100 px-3 py-2 text-center">
      <p className="text-2xl font-bold text-emerald-700">{value}</p>
      <p className="text-xs text-emerald-600">{label}</p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Dashboard page
// ---------------------------------------------------------------------------

export default function DashboardPage() {
  const router = useRouter()
  const [userEmail, setUserEmail] = useState<string | null>(null)
  const [backendOk, setBackendOk] = useState<boolean | null>(null)

  // Verify auth client-side (middleware already guards the route server-side)
  useEffect(() => {
    const supabase = createClient()
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (!user) {
        router.replace('/login')
      } else {
        setUserEmail(user.email ?? null)
      }
    })
  }, [router])

  // Backend health probe
  useEffect(() => {
    healthCheck().then(setBackendOk)
  }, [])

  async function handleLogout() {
    const supabase = createClient()
    await supabase.auth.signOut()
    router.push('/login')
    router.refresh()
  }

  return (
    <div className="flex flex-col h-full min-h-screen">
      {/* Top bar */}
      <header className="flex-none flex items-center justify-between gap-4 px-5 py-3 border-b border-zinc-200 bg-white shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white font-bold text-sm shadow">
            A
          </div>
          <span className="font-semibold text-zinc-900">AtlasAI</span>

          {/* Backend status pill */}
          {backendOk !== null && (
            <span
              className={`hidden sm:inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                backendOk
                  ? 'bg-emerald-100 text-emerald-700'
                  : 'bg-red-100 text-red-700'
              }`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  backendOk ? 'bg-emerald-500' : 'bg-red-500'
                }`}
              />
              {backendOk ? 'Backend online' : 'Backend offline'}
            </span>
          )}
        </div>

        <div className="flex items-center gap-4">
          {userEmail && (
            <span className="hidden sm:block text-xs text-zinc-500 truncate max-w-[200px]">
              {userEmail}
            </span>
          )}
          <button
            onClick={handleLogout}
            className="rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs font-medium text-zinc-600 shadow-sm transition-colors hover:bg-zinc-50 hover:text-zinc-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            Log out
          </button>
        </div>
      </header>

      {/* Two-panel layout */}
      <div className="flex flex-1 overflow-hidden divide-x divide-zinc-200">
        {/* Left — Chat */}
        <div className="flex-1 min-w-0 flex flex-col overflow-hidden">
          <ChatPanel />
        </div>

        {/* Right — Ingest */}
        <div className="w-80 flex-none flex flex-col overflow-hidden lg:w-96">
          <IngestPanel />
        </div>
      </div>
    </div>
  )
}
