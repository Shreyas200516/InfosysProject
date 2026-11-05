import { motion } from 'framer-motion'
import { Bot, BookOpen, ArrowUpFromLine } from 'lucide-react'

const POINTS = [
  { icon: BookOpen, text: 'Answers come only from your knowledge base, with sources.' },
  { icon: Bot, text: 'Four agents triage, search, resolve and decide, in seconds.' },
  { icon: ArrowUpFromLine, text: 'Anything risky or unclear goes to the right team.' },
]

/** Shared frame for the sign-in and sign-up screens: a dark brand panel beside a frosted form card. */
export default function AuthShell({ title, subtitle, children, footer }) {
  return (
    <div className="relative flex min-h-screen overflow-hidden bg-page">
      <div aria-hidden className="pointer-events-none absolute -right-32 -top-32 h-[28rem] w-[28rem] rounded-full bg-primary/20 blur-3xl" />
      <div aria-hidden className="pointer-events-none absolute -bottom-40 left-1/3 h-[26rem] w-[26rem] rounded-full bg-sidebar/10 blur-3xl" />

      <aside className="relative hidden w-[44%] max-w-[560px] flex-col justify-between bg-sidebar p-10 text-white lg:flex">
        <div className="flex items-center gap-2.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary"><svg viewBox="0 0 32 32" className="h-6 w-6" aria-hidden><path d="M7 22l9-15 9 15h-6l-3-5-3 5z" fill="#fff" /></svg></div>
          <span className="font-display text-2xl font-bold tracking-tight">SupportPilot</span>
        </div>
        <div>
          <h2 className="font-display text-4xl font-bold leading-tight">IT problems, solved before anyone has to wait.</h2>
          <ul className="mt-8 space-y-4">
            {POINTS.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-start gap-3 text-slate-300"><span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/10"><Icon className="h-4 w-4 text-primary" aria-hidden /></span>{text}</li>
            ))}
          </ul>
        </div>
        <p className="text-sm text-slate-400">Tickets in, resolutions out. People step in when it matters.</p>
      </aside>

      <main className="relative flex flex-1 items-center justify-center p-4 sm:p-8">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="frost w-full max-w-md rounded-3xl p-7 sm:p-9">
          <h1 className="font-display text-3xl font-bold text-heading">{title}</h1>
          <p className="muted mt-1 text-[15px]">{subtitle}</p>
          <div className="mt-6">{children}</div>
          <div className="mt-6 border-t border-line pt-5 text-center text-sm text-secondary">{footer}</div>
        </motion.div>
      </main>
    </div>
  )
}
