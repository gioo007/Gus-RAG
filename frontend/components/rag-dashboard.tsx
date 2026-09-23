'use client'

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useEffect, useRef, useState } from 'react'
import { ArrowUp, Link2, PanelRightClose, PanelRightOpen, Plus, Upload } from 'lucide-react'
import { ApiError, askQuestion, getSources, uploadFile, addWebUrl, deleteSource, type SourceInfo } from '@/lib/api'

type Message = { id: string; role: 'user' | 'assistant' | 'error'; content: string; sources?: SourceInfo[] }
type Source = { name: string; type: string }

function LightbulbIcon({ lit, className }: { lit: boolean; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      <g stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" className="transition-opacity duration-200" style={{ opacity: lit ? 1 : 0 }}>
        <line x1="19.3" y1="11" x2="22" y2="11" />
        <line x1="18.32" y1="7.35" x2="20.66" y2="6" />
        <line x1="15.65" y1="4.68" x2="17" y2="2.34" />
        <line x1="12" y1="3.7" x2="12" y2="1" />
        <line x1="8.35" y1="4.68" x2="7" y2="2.34" />
        <line x1="5.68" y1="7.35" x2="3.34" y2="6" />
        <line x1="4.7" y1="11" x2="2" y2="11" />
      </g>
      <path d="M12 5.1c-3.15 0-5.7 2.47-5.7 5.5 0 2 1.08 3.75 2.7 4.72v1.98c0 .5.4.9.9.9h4.2c.5 0 .9-.4.9-.9v-1.98c1.62-.97 2.7-2.72 2.7-4.72 0-3.03-2.55-5.5-5.7-5.5Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <line x1="9.6" y1="19.6" x2="14.4" y2="19.6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="9.85" y1="21.3" x2="14.15" y2="21.3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="10.3" y1="23" x2="13.7" y2="23" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  )
}

function newId() {
  // randomUUID only exists in secure contexts (https / localhost), so fall back for LAN dev over http
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
}

const THINK_HARDER_K = 10 // backend's QueryRequest.k allows 1–10; this is its ceiling

// Accepts "example.com/page" as well as full URLs; only http(s) with a real-looking host is allowed.
// Returns null when invalid. (new URL() alone is too lenient: some engines accept "https://not a url".)
function normalizeUrl(value: string) {
  if (/\s/.test(value)) return null
  const withScheme = /^[a-z][a-z\d+.-]*:\/\//i.test(value) ? value : `https://${value}`
  try {
    const url = new URL(withScheme)
    const isHttp = url.protocol === 'http:' || url.protocol === 'https:'
    const hasHost = url.hostname.includes('.') || url.hostname === 'localhost'
    return isHttp && hasHost ? url.href : null
  } catch {
    return null
  }
}

export function RagDashboard() {
  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  // Single chat, single session
  const [sessionId, setSessionId] = useState(newId)
  // rightOpen drives the mobile drawer; rightCollapsed drives the desktop panel.
  const [rightOpen, setRightOpen] = useState(false)
  const [rightCollapsed, setRightCollapsed] = useState(false)
  const [sources, setSources] = useState<Source[]>([])
  const [urlInput, setUrlInput] = useState('')
  const [urlError, setUrlError] = useState('')
  const [isAsking, setIsAsking] = useState(false)
  // "Think harder": widens retrieval from the backend's default k to THINK_HARDER_K (its schema max).
  const [thinkHarder, setThinkHarder] = useState(false)
  
  const fileInputRef = useRef<HTMLInputElement>(null)
  const urlDialogRef = useRef<HTMLDialogElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  
  // Tracks the in-flight /query/ request so New Chat (or an unmount) can cancel it.
  const inFlightRef = useRef<AbortController | null>(null)

  // Fetch initial sources from the backend on mount
  useEffect(() => {
    getSources()
      .then((data) => setSources(data.map((d) => ({ name: d.source, type: d.source_type || 'unknown' }))))
      .catch((err) => console.error('Failed to fetch initial sources:', err))
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages.length, isAsking])

  useEffect(() => () => inFlightRef.current?.abort(), [])

  async function submitQuery(event: React.FormEvent) {
    event.preventDefault()
    const text = query.trim()
    if (!text || isAsking) return

    setMessages((prev) => [...prev, { id: newId(), role: 'user', content: text }])
    setQuery('')
    setIsAsking(true)

    inFlightRef.current?.abort()
    const controller = new AbortController()
    inFlightRef.current = controller

    try {
      const result = await askQuestion(text, sessionId, { k: thinkHarder ? THINK_HARDER_K : undefined, signal: controller.signal })
      setMessages((prev) => [...prev, { id: newId(), role: 'assistant', content: result.answer, sources: result.sources }])
    } catch (error) {
      if (controller.signal.aborted) return // superseded by New Chat / unmount — not a real failure
      const message = error instanceof ApiError ? error.message : 'Something went wrong. Please try again.'
      setMessages((prev) => [...prev, { id: newId(), role: 'error', content: message }])
    } finally {
      if (inFlightRef.current === controller) {
        inFlightRef.current = null
        setIsAsking(false)
      }
    }
  }

  async function startNewChat() {
    inFlightRef.current?.abort()
    setIsAsking(false)
    setMessages([])
    setQuery('')
    setSessionId(newId())
    setRightOpen(false)

    // Capture current sources and clear locally immediately
    const currentSources = [...sources]
    setSources([])

    // Clear backend vectors so they don't bleed into the new chat
    for (const source of currentSources) {
      try {
        await deleteSource(source.name)
      } catch (error) {
        console.error(`Failed to clear source ${source.name} from backend:`, error)
      }
    }
  }

  function handleFilesSelected(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? [])
    // reset so picking the same file again still fires onChange
    event.target.value = ''
    if (files.length === 0) return
    uploadFiles(files)
  }

  async function uploadFiles(files: File[]) {
    for (const file of files) {
      try {
        const result = await uploadFile(file)
        setSources((prev) => [...prev, { name: result.source, type: result.source_type }])
      } catch (error) {
        console.error(`Failed to upload ${file.name}:`, error)
      }
    }
  }

  function resetUrlDialog() {
    setUrlInput('')
    setUrlError('')
  }

  function submitUrl(event: React.FormEvent) {
    event.preventDefault()
    const url = normalizeUrl(urlInput.trim())
    if (!url) {
      setUrlError('Enter a valid web address, e.g. https://example.com/page')
      return
    }
    addUrl(url)
    urlDialogRef.current?.close()
  }

  async function addUrl(url: string) {
    try {
      const result = await addWebUrl(url)
      setSources((prev) => [...prev, { name: result.source, type: result.source_type }])
    } catch (error) {
      console.error(`Failed to ingest URL ${url}:`, error)
    }
  }

  return (
    <main className="relative flex h-screen min-h-screen flex-row overflow-hidden bg-[#2A0A10] text-[#FBF6EE]">
      {rightOpen && <div aria-hidden="true" onClick={() => setRightOpen(false)} className="fixed inset-0 z-40 bg-black/50 backdrop-blur-md md:hidden" />}

      <header className="absolute inset-x-0 top-0 z-30 flex h-14 items-center justify-end px-4 md:hidden">
        <button aria-label="Open sources" onClick={() => setRightOpen(true)} className="rounded p-1.5 text-[#D8C4B6] hover:bg-white/[0.06]"><PanelRightOpen className="size-4" /></button>
      </header>

      <section className="relative z-0 flex min-w-0 flex-1 flex-col bg-[#2A0A10]">
        {rightCollapsed && <button aria-label="Open sources" onClick={() => setRightCollapsed(false)} className="absolute right-4 top-4 z-30 hidden rounded p-1.5 text-[#D8C4B6] hover:bg-white/[0.06] md:block"><PanelRightOpen className="size-4" /></button>}
        {messages.length > 0 && <div className="pointer-events-none absolute inset-x-0 top-0 z-20 flex h-14 items-center justify-center md:h-12"><span className="font-serif text-lg text-[#D8C4B6]">Gus</span></div>}
        {messages.length > 0 ? (
          <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-40 pt-16 md:px-10 md:pt-12">
            <div className="mx-auto flex max-w-3xl flex-col gap-6">
              {messages.map((message) => {
                if (message.role === 'user') return <p key={message.id} className="max-w-[85%] self-end whitespace-pre-wrap break-words rounded-md bg-[#1E0B11] px-4 py-2.5 text-sm leading-6">{message.content}</p>
                if (message.role === 'error') return <p key={message.id} className="whitespace-pre-wrap break-words text-sm leading-7 text-[#F2A7A7]">{message.content}</p>
                return (
                  <div key={message.id} className="flex flex-col gap-2">
                    <div className="prose prose-invert prose-sm max-w-none text-[#FBF6EE] prose-headings:text-[#FBF6EE] prose-a:text-[#D8C4B6] prose-code:text-[#D8C4B6] prose-pre:border prose-pre:border-white/10 prose-pre:bg-[#1E0B11]">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {message.content}
                      </ReactMarkdown>
                    </div>
                    {message.sources && message.sources.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1.5">
                        {message.sources.map((s, idx) => (
                          <span key={idx} className="rounded-sm border border-white/[0.08] bg-[#1E0B11] px-2 py-0.5 text-[11px] text-[#D8C4B6]">
                            {s.source}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
              {isAsking && <div aria-label="Waiting for a response" className="flex gap-1.5 py-1">{[0, 1, 2].map((i) => <span key={i} style={{ animationDelay: `${i * 0.15}s` }} className="size-1.5 animate-bounce rounded-full bg-[#D8C4B6]/60" />)}</div>}
              <div ref={bottomRef} />
            </div>
          </div>
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center px-6 pb-32 pt-16 md:pt-12">
            <div className="flex max-w-2xl -translate-y-10 flex-col items-center text-center md:-translate-y-14"><p className="mb-5 font-serif text-3xl text-[#D8C4B6]">Gus</p><h1 className="font-serif text-4xl tracking-tight sm:text-5xl">What would you like to explore?</h1><p className="mt-4 text-sm text-[#D8C4B6]">Ask a question across your connected sources.</p></div>
          </div>
        )}
        <div className="pointer-events-none absolute bottom-0 left-0 right-0 bg-linear-to-t from-[#2A0A10] from-60% to-transparent px-5 pb-7 pt-10 md:px-10"><form onSubmit={submitQuery} className="pointer-events-auto mx-auto max-w-3xl"><div className="flex items-center rounded-md border border-[#0B101E] bg-[#1E0B11] p-2"><input value={query} onChange={(event) => setQuery(event.target.value)} disabled={isAsking} placeholder="Write a message..." className="min-w-0 flex-1 bg-transparent px-3 py-2 text-sm outline-none placeholder:text-[#9F7F7E] disabled:opacity-60" /><button type="button" aria-pressed={thinkHarder} aria-label="Think harder: broader retrieval" title="Think harder: broader retrieval" onClick={() => setThinkHarder((value) => !value)} className={`mr-1.5 flex size-9 shrink-0 items-center justify-center rounded-md transition-all duration-200 ${thinkHarder ? 'bg-[#FBF6EE] text-[#2A0A10]' : 'text-[#D8C4B6] hover:bg-white/[0.06]'}`}><LightbulbIcon lit={thinkHarder} className="size-[18px]" /></button><button aria-label="Send query" type="submit" disabled={isAsking || !query.trim()} className="flex size-9 shrink-0 items-center justify-center rounded-md bg-[#FBF6EE] text-[#2A0A10] transition-all duration-200 hover:brightness-90 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:brightness-100"><ArrowUp className="size-4" /></button></div><p className="mt-2 text-center text-[10px] text-[#9F7F7E]">Gus can make mistakes. Verify important information in the original sources.</p></form></div>
      </section>

      <aside className={`fixed inset-y-0 right-0 z-50 flex h-full w-[75vw] flex-col overflow-hidden border-l border-[#120408] bg-[#1E0B11] shadow-2xl transition-[translate,visibility] duration-300 md:relative md:z-auto md:shrink-0 md:translate-x-0 md:shadow-none md:transition-[width,visibility] ${rightOpen ? 'translate-x-0' : 'translate-x-full max-md:invisible'} ${rightCollapsed ? 'md:invisible md:w-0 md:border-l-0' : 'md:w-[330px]'}`}>
        <div className="flex h-full w-full flex-col px-5 py-6 md:w-[330px]">
          <div className="flex items-center justify-between"><h2 className="font-serif text-2xl">Sources</h2><button aria-label="Close sources" onClick={() => setRightOpen(false)} className="rounded p-1.5 text-[#D8C4B6] hover:bg-white/[0.06] md:hidden"><PanelRightClose className="size-4" /></button><button aria-label="Collapse sources" onClick={() => setRightCollapsed(true)} className="hidden rounded p-1.5 text-[#D8C4B6] hover:bg-white/[0.06] md:block"><PanelRightClose className="size-4" /></button></div>
          <div className="mt-4 flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto">
            {sources.length === 0
              ? <p className="text-xs text-[#D8C4B6]/70">No sources yet. Upload a file or add a URL to get started.</p>
              : sources.map((source) => <div key={source.name} className="shrink-0 border-b border-white/[0.06] pb-3"><p className="truncate text-sm text-[#FBF6EE]">{source.name}</p><p className="mt-1 text-xs text-[#D8C4B6]/70">{source.type}</p></div>)}
          </div>
          <div className="mt-4 grid grid-cols-3 gap-2 border-t border-white/[0.06] pt-4">
            <button onClick={startNewChat} className="flex flex-col items-center justify-center gap-1 rounded-md bg-[#FBF6EE] px-1 py-2.5 text-center text-[10px] font-bold leading-tight text-[#0B101E] transition-all duration-200 hover:brightness-90"><Plus className="size-4" /> New Chat</button>
            <input ref={fileInputRef} type="file" multiple hidden onChange={handleFilesSelected} accept=".pdf,.docx,.zip" />
            <button onClick={() => fileInputRef.current?.click()} className="flex flex-col items-center justify-center gap-1 rounded-md bg-[#FBF6EE] px-1 py-2.5 text-center text-[10px] font-bold leading-tight text-[#0B101E] transition-all duration-200 hover:brightness-90"><Upload className="size-4" /> Upload Files</button>
            <button onClick={() => urlDialogRef.current?.showModal()} className="flex flex-col items-center justify-center gap-1 rounded-md bg-[#FBF6EE] px-1 py-2.5 text-center text-[10px] font-bold leading-tight text-[#0B101E] transition-all duration-200 hover:brightness-90"><Link2 className="size-4" /> Add URL</button>
          </div>
        </div>
      </aside>

      <dialog ref={urlDialogRef} onClose={resetUrlDialog} onClick={(event) => { if (event.target === event.currentTarget) event.currentTarget.close() }} className="m-auto w-[min(92vw,420px)] rounded-md border border-[#120408] bg-[#1E0B11] p-0 text-[#FBF6EE] shadow-2xl backdrop:bg-black/50 backdrop:backdrop-blur-md">
        <form onSubmit={submitUrl} noValidate className="flex flex-col gap-4 p-5">
          <h2 className="font-serif text-2xl">Add URL</h2>
          <label htmlFor="source-url" className="sr-only">Web page URL</label>
          <input id="source-url" type="url" inputMode="url" autoComplete="off" value={urlInput} onChange={(event) => { setUrlInput(event.target.value); setUrlError('') }} placeholder="https://example.com/page" aria-invalid={urlError ? true : undefined} className="w-full rounded-md border border-[#0B101E] bg-[#2A0A10] px-3 py-2 text-sm outline-none placeholder:text-[#9F7F7E] focus:border-[#D8C4B6]" />
          {urlError && <p role="alert" className="text-xs text-[#F2A7A7]">{urlError}</p>}
          <div className="flex justify-end gap-2"><button type="button" onClick={() => urlDialogRef.current?.close()} className="rounded-md px-3 py-2 text-xs text-[#D8C4B6] hover:bg-white/[0.06]">Cancel</button><button type="submit" className="rounded-md bg-[#FBF6EE] px-3 py-2 text-xs font-bold text-[#0B101E]">Add</button></div>
        </form>
      </dialog>
    </main>
  )
}