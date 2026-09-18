'use client'

import { useState } from 'react'
import { ArrowUp, Check, Link2, PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen, Plus, Upload } from 'lucide-react'

const chats = ['Financial mathematics', 'User interviews', 'Q3 market analysis', 'Product positioning', 'Competitive landscape']
const sources = [
  { name: 'Annual Report 2024.pdf', meta: 'PDF · 42 pages' },
  { name: 'Market Research Notes', meta: 'DOCX · 18 pages' },
  { name: 'company.com/insights', meta: 'URL · Web source' },
]

export function RagDashboard() {
  const [query, setQuery] = useState('')
  const [sent, setSent] = useState(false)
  const [activeChat, setActiveChat] = useState(chats[0])
  const [leftOpen, setLeftOpen] = useState(false)
  const [rightOpen, setRightOpen] = useState(false)

  function submitQuery(event: React.FormEvent) {
    event.preventDefault()
    if (!query.trim()) return
    setSent(true)
    setQuery('')
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

      <aside className={`fixed inset-y-0 left-0 z-50 flex h-full w-[75vw] flex-col overflow-hidden border-r border-[#120408] bg-[#1E0B11] px-5 py-6 shadow-2xl transition-transform duration-300 md:relative md:z-auto md:w-[250px] md:shrink-0 md:translate-x-0 md:shadow-none ${leftOpen ? 'translate-x-0 md:flex' : '-translate-x-full md:translate-x-0 md:flex'}`}>
        <div className="flex items-center justify-between"><h2 className="font-serif text-2xl">Chats</h2><button aria-label="Collapse chat history" onClick={() => setLeftOpen(false)} className="rounded p-1.5 text-[#D8C4B6] hover:bg-white/[0.06]"><PanelLeftClose className="size-4" /></button></div>
        <nav className="mt-10 flex flex-col gap-0.5 overflow-hidden">{chats.map((chat) => <button key={chat} onClick={() => setActiveChat(chat)} className={`truncate py-1 text-left text-sm leading-5 ${activeChat === chat ? 'text-[#FBF6EE]' : 'text-[#D8C4B6]/70 hover:text-[#FBF6EE]'}`}>{chat}</button>)}</nav>
        <button className="mt-auto flex w-full items-center justify-center rounded-md bg-[#FBF6EE] px-3 py-2 text-xs font-bold text-[#0B101E]"><Plus className="mr-2 size-4" /> New Chat</button>
      </aside>

      <section className="relative z-0 flex min-w-0 flex-1 flex-col bg-[#2A0A10]">
        <div className="flex flex-1 flex-col items-center justify-center px-6 pb-32 pt-16 md:pt-12">
          {sent ? <div className="flex max-w-lg flex-col items-center gap-4 text-center"><div className="flex size-12 items-center justify-center rounded-full bg-[#0B101E]"><Check className="size-5" /></div><h1 className="font-serif text-4xl">Query received</h1><p className="text-sm leading-6 text-[#D8C4B6]">Your question is ready for the RAG pipeline.</p><button onClick={() => setSent(false)} className="text-sm underline underline-offset-4">Ask another question</button></div> : <div className="flex max-w-2xl flex-col items-center text-center"><p className="mb-5 text-3xl text-[#D8C4B6] [font-family:'Old_English_Text_MT','UnifrakturCook','Blackletter',serif]">Gus</p><h1 className="font-serif text-4xl tracking-tight sm:text-5xl">What would you like to explore?</h1><p className="mt-4 text-sm text-[#D8C4B6]">Ask a question across your connected sources.</p></div>}
        </div>
        <div className="absolute bottom-0 left-0 right-0 px-5 pb-7 md:px-10"><form onSubmit={submitQuery} className="mx-auto max-w-3xl"><div className="flex items-center rounded-md border border-[#0B101E] bg-[#1E0B11] p-2"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Let's begin..." className="min-w-0 flex-1 bg-transparent px-3 py-2 text-sm outline-none placeholder:text-[#9F7F7E]" /><button aria-label="Send query" type="submit" className="flex size-9 items-center justify-center rounded-md bg-[#FBF6EE] text-[#2A0A10]"><ArrowUp className="size-4" /></button></div><p className="mt-2 text-center text-[10px] text-[#9F7F7E]">Gus can make mistakes. Verify important information in the original sources.</p></form></div>
      </section>

      <aside className={`fixed inset-y-0 right-0 z-50 flex h-full w-[75vw] flex-col overflow-hidden border-l border-[#120408] bg-[#1E0B11] px-5 py-6 shadow-2xl transition-transform duration-300 md:relative md:z-auto md:w-[285px] md:shrink-0 md:translate-x-0 md:shadow-none ${rightOpen ? 'translate-x-0 md:flex' : 'translate-x-full md:translate-x-0 md:flex'}`}>
        <div className="flex items-center justify-between"><h2 className="font-serif text-2xl">Sources</h2><button aria-label="Collapse sources" onClick={() => setRightOpen(false)} className="rounded p-1.5 text-[#D8C4B6] hover:bg-white/[0.06]"><PanelRightClose className="size-4" /></button></div>
        <div className="mt-6 flex max-h-48 flex-col gap-3 overflow-hidden">{sources.map((source) => <div key={source.name} className="border-b border-white/[0.06] pb-4"><p className="truncate text-sm text-[#FBF6EE]">{source.name}</p><p className="mt-1 text-xs text-[#D8C4B6]/70">{source.meta}</p></div>)}</div>
        <div className="mt-auto flex flex-col gap-2 pt-8"><button className="flex items-center justify-center rounded-md bg-[#FBF6EE] px-3 py-2 text-xs font-bold text-[#0B101E]"><Upload className="mr-2 size-4" /> Upload Files</button><button className="flex items-center justify-center rounded-md bg-[#FBF6EE] px-3 py-2 text-xs font-bold text-[#0B101E]"><Link2 className="mr-2 size-4" /> Add URL</button></div>
      </aside>
    </main>
  )
}
