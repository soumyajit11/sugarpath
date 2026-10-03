import { useState } from 'react'
import { Bell, HeartPulse, Home, LineChart, MessageCircle, MoreHorizontal, Pill } from 'lucide-react'

export type Page = 'home' | 'glucose' | 'medicine' | 'meals' | 'activity' | 'sleep' | 'ask' | 'memory' | 'report' | 'notifications'

const primary: { page: Page; label: string; icon: typeof Home }[] = [
  { page: 'home', label: 'Home', icon: Home }, { page: 'glucose', label: 'Glucose', icon: LineChart },
  { page: 'medicine', label: 'Medicine', icon: Pill }, { page: 'ask', label: 'Ask', icon: MessageCircle },
]
const secondary: { page: Page; label: string }[] = [
  { page: 'meals', label: 'Meals' }, { page: 'activity', label: 'Activity' }, { page: 'sleep', label: 'Sleep' },
  { page: 'report', label: 'Weekly report' }, { page: 'memory', label: 'Memory' }, { page: 'notifications', label: 'Notifications' },
]

export function AppShell({ page, setPage, unread, children }: { page: Page; setPage: (page: Page) => void; unread: number; children: React.ReactNode }) {
  const [moreOpen, setMoreOpen] = useState(false)
  const selectPage = (nextPage: Page) => { setPage(nextPage); setMoreOpen(false) }
  const moreSelected = secondary.some(item => item.page === page)
  return <main className="app-shell">
    <header className="app-header"><div className="brand"><HeartPulse aria-hidden="true"/><span>Sugar Path</span></div><div className="header-actions"><button className="bell-button" aria-label={`${unread} unread notifications`} onClick={() => selectPage('notifications')}><Bell aria-hidden="true"/>{unread > 0 && <b>{unread}</b>}</button><span className="demo">Demo data only</span></div></header>
    <aside className="desktop-nav" aria-label="Primary navigation">{primary.map(item => <NavButton key={item.page} item={item} active={page === item.page} setPage={selectPage}/>)}{secondary.map(item => <button key={item.page} className={page === item.page ? 'active' : ''} onClick={() => selectPage(item.page)}>{item.label}</button>)}</aside>
    <div className="page-content">{children}</div>
    {moreOpen && <div className="more-menu" aria-label="More pages">{secondary.map(item => <button key={item.page} className={page === item.page ? 'active' : ''} onClick={() => selectPage(item.page)}>{item.label}</button>)}</div>}
    <nav className="mobile-nav" aria-label="Primary navigation">{primary.map(item => <NavButton key={item.page} item={item} active={page === item.page} setPage={selectPage}/>)}<button className={moreSelected ? 'active' : ''} aria-expanded={moreOpen} onClick={() => setMoreOpen(!moreOpen)}><MoreHorizontal aria-hidden="true"/><span>More</span></button></nav>
  </main>
}

function NavButton({ item, active, setPage }: { item: { page: Page; label: string; icon: typeof Home }; active: boolean; setPage: (page: Page) => void }) { const Icon = item.icon; return <button className={active ? 'active' : ''} onClick={() => setPage(item.page)}><Icon aria-hidden="true"/><span>{item.label}</span></button> }

export function PageHeader({ title, subtitle, action }: { title: string; subtitle: string; action?: React.ReactNode }) { return <div className="page-header"><div><h1>{title}</h1><p>{subtitle}</p></div>{action}</div> }
