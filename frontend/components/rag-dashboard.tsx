'use client'

import { useEffect, useRef, useState } from 'react'
import { ArrowUp, Link2, PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen, Plus, Upload } from 'lucide-react'

type Message = { id: string; role: 'user' | 'assistant'; content: string }
type Chat = { id: string; title: string; messages: Message[] }

function newId() {
  // randomUUID only exists in secure contexts (https / localhost), so fall back for LAN dev over http
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
}

function mockChat(id: string, title: string, question: string, answer: string): Chat {
  return {
    id,
    title,
    messages: [
      { id: `${id}-q`, role: 'user', content: question },
      { id: `${id}-a`, role: 'assistant', content: answer }
    ]
  }
}

// Mock fixtures — replaced by the backend's list-sessions / session-history endpoints in Phase 4
const initialChats: Chat[] = [
  mockChat('financial-mathematics', 'Financial mathematics', 'What is the difference between simple and compound interest?', 'Simple interest accrues only on the original principal. Compound interest accrues on the principal plus previously earned interest, so the balance grows faster over time.'),
  mockChat('user-interviews', 'User interviews', 'What themes come up most in the user interviews?', 'Across the interviews, participants most often raised onboarding friction and difficulty finding previously saved work.'),
  mockChat('q3-market-analysis', 'Q3 market analysis', 'Summarize the Q3 market analysis in two sentences.', 'Demand held steady through the quarter while pricing pressure increased in the mid-market segment. Supply costs were flagged as the main risk heading into Q4.'),
  mockChat('product-positioning', 'Product positioning', 'How should we position the product against incumbents?', 'Lead with speed of setup and transparent pricing, and avoid competing on breadth of features where incumbents are strongest.'),
  mockChat('competitive-landscape', 'Competitive landscape', 'Who are the main competitors in this space?', 'The market splits into a few large incumbents and a growing group of niche entrants focused on specific industries.')
]

// TODO(phase 2): replaced by the real answer from the backend
const PLACEHOLDER_REPLY = 'Query received. Your question is ready for the RAG pipeline.'

const sources = [
  { name: 'Annual Report 2024.pdf', meta: 'PDF · 42 pages' },
  { name: 'Market Research Notes', meta: 'DOCX · 18 pages' },
  { name: 'company.com/insights', meta: 'URL · Web source' },
]

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
  const [chats, setChats] = useState<Chat[]>(initialChats)
  // The active chat id doubles as the session id. A fresh id with no matching chat is an unsent draft.
  const [activeChatId, setActiveChatId] = useState(newId)
  // leftOpen/rightOpen drive the mobile drawers; leftCollapsed/rightCollapsed drive the desktop panels.
  const [leftOpen, setLeftOpen] = useState(false)
  const [rightOpen, setRightOpen] = useState(false)
  const [leftCollapsed, setLeftCollapsed] = useState(false)
  const [rightCollapsed, setRightCollapsed] = useState(false)
  const [urlInput, setUrlInput] = useState('')
  const [urlError, setUrlError] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const urlDialogRef = useRef<HTMLDialogElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  const messages = chats.find((chat) => chat.id === activeChatId)?.messages ?? []

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [activeChatId, messages.length])

  function submitQuery(event: React.FormEvent) {
    event.preventDefault()
    const text = query.trim()
    if (!text) return
    // TODO(phase 2): POST the query (with activeChatId as the session id) and append the real answer
    const turn: Message[] = [
      { id: newId(), role: 'user', content: text },
      { id: newId(), role: 'assistant', content: PLACEHOLDER_REPLY }
    ]
    setChats((prev) =>
      prev.some((chat) => chat.id === activeChatId)
        ? prev.map((chat) => (chat.id === activeChatId ? { ...chat, messages: [...chat.messages, ...turn] } : chat))
        : [{ id: activeChatId, title: text.length > 40 ? `${text.slice(0, 40).trimEnd()}…` : text, messages: turn }, ...prev]
    )
    setQuery('')
  }

  function startNewChat() {
    setQuery('')
    setActiveChatId(newId())
    setLeftOpen(false)
  }

  function selectChat(id: string) {
    setActiveChatId(id)
    setLeftOpen(false)
  }

  function handleFilesSelected(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? [])
    // reset so picking the same file again still fires onChange
    event.target.value = ''
    if (files.length === 0) return
    uploadFiles(files)
  }

  function uploadFiles(files: File[]) {
    // TODO(phase 3): POST to the ingest endpoint, show progress, refresh the sources list
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
    // TODO(phase 3): POST to the scrape/ingest endpoint, then refresh the sources list
    console.debug('[gus] url submitted:', url)
  }

  function openLeft() {
    setLeftOpen(true)
    setRightOpen(false)
  }

  function openRight() {
    setRightOpen(true)
    setLeftOpen(false)
  }

  return (
    <main className="relative flex h-screen min-h-screen flex-row overflow-hidden bg-[#2A0A10] text-[#FBF6EE]">
      {(leftOpen || rightOpen) && <div aria-hidden="true" onClick={() => { setLeftOpen(false); setRightOpen(false) }} className="fixed inset-0 z-40 bg-black/50 backdrop-blur-md md:hidden" />}

      <header className="absolute inset-x-0 top-0 z-30 flex h-14 items-center justify-between px-4 md:hidden">
        <button aria-label="Open chat history" onClick={openLeft} className="rounded p-1.5 text-[#D8C4B6] hover:bg-white/[0.06]"><PanelLeftOpen className="size-4" /></button>
        <span className="font-serif text-lg">Gus</span>
        <button aria-label="Open sources" onClick={openRight} className="rounded p-1.5 text-[#D8C4B6] hover:bg-white/[0.06]"><PanelRightOpen className="size-4" /></button>
      </header>

      <aside className={`fixed inset-y-0 left-0 z-50 flex h-full w-[75vw] flex-col overflow-hidden border-r border-[#120408] bg-[#1E0B11] shadow-2xl transition-[translate,visibility] duration-300 md:relative md:z-auto md:shrink-0 md:translate-x-0 md:shadow-none md:transition-[width,visibility] ${leftOpen ? 'translate-x-0' : '-translate-x-full max-md:invisible'} ${leftCollapsed ? 'md:invisible md:w-0 md:border-r-0' : 'md:w-[250px]'}`}>
        <div className="flex h-full w-full flex-col px-5 py-6 md:w-[250px]">
          <div className="flex items-center justify-between"><h2 className="font-serif text-2xl">Chats</h2><button aria-label="Close chat history" onClick={() => setLeftOpen(false)} className="rounded p-1.5 text-[#D8C4B6] hover:bg-white/[0.06] md:hidden"><PanelLeftClose className="size-4" /></button><button aria-label="Collapse chat history" onClick={() => setLeftCollapsed(true)} className="hidden rounded p-1.5 text-[#D8C4B6] hover:bg-white/[0.06] md:block"><PanelLeftClose className="size-4" /></button></div>
          <nav className="mt-10 flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto">{chats.map((chat) => <button key={chat.id} onClick={() => selectChat(chat.id)} aria-current={activeChatId === chat.id ? 'true' : undefined} className={`shrink-0 truncate py-1 text-left text-sm leading-5 ${activeChatId === chat.id ? 'text-[#FBF6EE]' : 'text-[#D8C4B6]/70 hover:text-[#FBF6EE]'}`}>{chat.title}</button>)}</nav>
          <button onClick={startNewChat} className="mt-4 flex w-full items-center justify-center rounded-md bg-[#FBF6EE] px-3 py-2 text-xs font-bold text-[#0B101E]"><Plus className="mr-2 size-4" /> New Chat</button>
        </div>
      </aside>

      <section className="relative z-0 flex min-w-0 flex-1 flex-col bg-[#2A0A10]">
        {leftCollapsed && <button aria-label="Open chat history" onClick={() => setLeftCollapsed(false)} className="absolute left-4 top-4 z-30 hidden rounded p-1.5 text-[#D8C4B6] hover:bg-white/[0.06] md:block"><PanelLeftOpen className="size-4" /></button>}
        {rightCollapsed && <button aria-label="Open sources" onClick={() => setRightCollapsed(false)} className="absolute right-4 top-4 z-30 hidden rounded p-1.5 text-[#D8C4B6] hover:bg-white/[0.06] md:block"><PanelRightOpen className="size-4" /></button>}
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
            <div className="flex max-w-2xl flex-col items-center text-center"><p className="mb-5 text-3xl text-[#D8C4B6] [font-family:'Old_English_Text_MT','UnifrakturCook','Blackletter',serif]">Gus</p><h1 className="font-serif text-4xl tracking-tight sm:text-5xl">What would you like to explore?</h1><p className="mt-4 text-sm text-[#D8C4B6]">Ask a question across your connected sources.</p></div>
          </div>
        )}
        <div className="pointer-events-none absolute bottom-0 left-0 right-0 bg-linear-to-t from-[#2A0A10] from-60% to-transparent px-5 pb-7 pt-10 md:px-10"><form onSubmit={submitQuery} className="pointer-events-auto mx-auto max-w-3xl"><div className="flex items-center rounded-md border border-[#0B101E] bg-[#1E0B11] p-2"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Let's begin..." className="min-w-0 flex-1 bg-transparent px-3 py-2 text-sm outline-none placeholder:text-[#9F7F7E]" /><button aria-label="Send query" type="submit" className="flex size-9 items-center justify-center rounded-md bg-[#FBF6EE] text-[#2A0A10]"><ArrowUp className="size-4" /></button></div><p className="mt-2 text-center text-[10px] text-[#9F7F7E]">Gus can make mistakes. Verify important information in the original sources.</p></form></div>
      </section>

      <aside className={`fixed inset-y-0 right-0 z-50 flex h-full w-[75vw] flex-col overflow-hidden border-l border-[#120408] bg-[#1E0B11] shadow-2xl transition-[translate,visibility] duration-300 md:relative md:z-auto md:shrink-0 md:translate-x-0 md:shadow-none md:transition-[width,visibility] ${rightOpen ? 'translate-x-0' : 'translate-x-full max-md:invisible'} ${rightCollapsed ? 'md:invisible md:w-0 md:border-l-0' : 'md:w-[285px]'}`}>
        <div className="flex h-full w-full flex-col px-5 py-6 md:w-[285px]">
          <div className="flex items-center justify-between"><h2 className="font-serif text-2xl">Sources</h2><button aria-label="Close sources" onClick={() => setRightOpen(false)} className="rounded p-1.5 text-[#D8C4B6] hover:bg-white/[0.06] md:hidden"><PanelRightClose className="size-4" /></button><button aria-label="Collapse sources" onClick={() => setRightCollapsed(true)} className="hidden rounded p-1.5 text-[#D8C4B6] hover:bg-white/[0.06] md:block"><PanelRightClose className="size-4" /></button></div>
          <div className="mt-6 flex max-h-48 flex-col gap-3 overflow-hidden">{sources.map((source) => <div key={source.name} className="border-b border-white/[0.06] pb-4"><p className="truncate text-sm text-[#FBF6EE]">{source.name}</p><p className="mt-1 text-xs text-[#D8C4B6]/70">{source.meta}</p></div>)}</div>
          <div className="mt-auto flex flex-col gap-2 pt-8"><input ref={fileInputRef} type="file" multiple hidden onChange={handleFilesSelected} /><button onClick={() => fileInputRef.current?.click()} className="flex items-center justify-center rounded-md bg-[#FBF6EE] px-3 py-2 text-xs font-bold text-[#0B101E]"><Upload className="mr-2 size-4" /> Upload Files</button><button onClick={() => urlDialogRef.current?.showModal()} className="flex items-center justify-center rounded-md bg-[#FBF6EE] px-3 py-2 text-xs font-bold text-[#0B101E]"><Link2 className="mr-2 size-4" /> Add URL</button></div>
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