'use client'

import { useEffect, useRef, useState } from 'react'
import { ArrowUp, Link2, PanelRightClose, PanelRightOpen, Plus, Upload } from 'lucide-react'

type Message = { id: string; role: 'user' | 'assistant'; content: string }
type Source = { name: string; type: string }

function newId() {
  // randomUUID only exists in secure contexts (https / localhost), so fall back for LAN dev over http
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
}

// Mock fixture — replaced by a real GET /documents/ fetch in Phase 3. Only name + type are shown;
// the backend's list endpoint returns chunk_count too, but the product decision is to hide it.
const initialSources: Source[] = [
  { name: 'Annual Report 2024.pdf', type: 'pdf' },
  { name: 'Market Research Notes.docx', type: 'docx' },
  { name: 'https://company.com/insights', type: 'web' },
]

// TODO(phase 2): replaced by the real answer from the backend
const PLACEHOLDER_REPLY = 'Query received. Your question is ready for the RAG pipeline.'

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
  // Single chat, single session — this id is sent as query.session_id once Phase 2 wires the API.
  const [sessionId, setSessionId] = useState(newId)
  // rightOpen drives the mobile drawer; rightCollapsed drives the desktop panel.
  const [rightOpen, setRightOpen] = useState(false)
  const [rightCollapsed, setRightCollapsed] = useState(false)
  const [sources, setSources] = useState<Source[]>(initialSources)
  const [urlInput, setUrlInput] = useState('')
  const [urlError, setUrlError] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const urlDialogRef = useRef<HTMLDialogElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages.length])

  function submitQuery(event: React.FormEvent) {
    event.preventDefault()
    const text = query.trim()
    if (!text) return
    // TODO(phase 2): POST { question: text, session_id: sessionId } and append the real answer
    setMessages((prev) => [...prev, { id: newId(), role: 'user', content: text }, { id: newId(), role: 'assistant', content: PLACEHOLDER_REPLY }])
    setQuery('')
  }

  function startNewChat() {
    // Product decision: one chat at a time. Starting a new one wipes this session's sources and
    // history everywhere, not just on screen.
    // TODO(phase 3/4): before resetting locally, DELETE /documents/{source} for everything in
    // `sources` (or a bulk-clear endpoint, if we add one) and clear this session's server-side
    // chat history, so nothing from the old session carries over.
    // Tab/browser close should do the same, but that can't be done reliably from the client —
    // beforeunload/pagehide can't guarantee a DELETE request completes, and sendBeacon only
    // supports POST. That cleanup belongs on the backend (a session TTL/reaper), not here.
    setMessages([])
    setSources([])
    setQuery('')
    setSessionId(newId())
    setRightOpen(false)
  }

  function handleFilesSelected(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? [])
    // reset so picking the same file again still fires onChange
    event.target.value = ''
    if (files.length === 0) return
    uploadFiles(files)
  }

  function uploadFiles(files: File[]) {
    // TODO(phase 3): POST each file to /documents/upload (one file per request), show progress,
    // append the returned { source, source_type } to `sources` on success
    console.debug('[gus] files selected:', files.map((file) => file.name))
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

  function addUrl(url: string) {
    // TODO(phase 3): POST { url } to /documents/web, then append the returned source on success
    console.debug('[gus] url submitted:', url)
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
              {messages.map((message) => message.role === 'user'
                ? <p key={message.id} className="max-w-[85%] self-end whitespace-pre-wrap break-words rounded-md bg-[#1E0B11] px-4 py-2.5 text-sm leading-6">{message.content}</p>
                : <p key={message.id} className="whitespace-pre-wrap break-words text-sm leading-7 text-[#FBF6EE]">{message.content}</p>)}
              <div ref={bottomRef} />
            </div>
          </div>
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center px-6 pb-32 pt-16 md:pt-12">
            <div className="flex max-w-2xl -translate-y-10 flex-col items-center text-center md:-translate-y-14"><p className="mb-5 font-serif text-3xl text-[#D8C4B6]">Gus</p><h1 className="font-serif text-4xl tracking-tight sm:text-5xl">What would you like to explore?</h1><p className="mt-4 text-sm text-[#D8C4B6]">Ask a question across your connected sources.</p></div>
          </div>
        )}
        <div className="pointer-events-none absolute bottom-0 left-0 right-0 bg-linear-to-t from-[#2A0A10] from-60% to-transparent px-5 pb-7 pt-10 md:px-10"><form onSubmit={submitQuery} className="pointer-events-auto mx-auto max-w-3xl"><div className="flex items-center rounded-md border border-[#0B101E] bg-[#1E0B11] p-2"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Write a message..." className="min-w-0 flex-1 bg-transparent px-3 py-2 text-sm outline-none placeholder:text-[#9F7F7E]" /><button aria-label="Send query" type="submit" className="flex size-9 items-center justify-center rounded-md bg-[#FBF6EE] text-[#2A0A10] transition-all duration-200 hover:brightness-90"><ArrowUp className="size-4" /></button></div><p className="mt-2 text-center text-[10px] text-[#9F7F7E]">Gus can make mistakes. Verify important information in the original sources.</p></form></div>
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