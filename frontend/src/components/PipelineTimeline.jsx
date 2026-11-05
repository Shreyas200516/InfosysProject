import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Stethoscope, BookOpen, Wand2, ArrowUpFromLine, CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import { ms, summarizeRun } from '../lib/format'

const ICONS = {
  'Diagnosis Agent': Stethoscope, 'Knowledge Retrieval Agent': BookOpen, 'Resolution Agent': Wand2, 'Escalation Agent': ArrowUpFromLine,
}

/** Agent pipeline. With `live` the agents reveal one by one, as they ran. */
export default function PipelineTimeline({ runs, live = false, onDone }) {
  const [shown, setShown] = useState(live ? 0 : runs.length)
  useEffect(() => {
    if (!live) { setShown(runs.length); return undefined }
    setShown(0)
    const timers = runs.map((_, i) => setTimeout(() => setShown(i + 1), 650 * (i + 1)))
    const done = setTimeout(() => onDone && onDone(), 650 * (runs.length + 1))
    return () => { timers.forEach(clearTimeout); clearTimeout(done) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [live, runs.length])

  return (
    <ol className="relative space-y-3 pl-1">
      {runs.map((r, i) => {
        const Icon = ICONS[r.agent_name] || Wand2
        const visible = i < shown
        const active = live && i === shown
        const failed = r.status === 'failed'
        return (
          <li key={r.run_id} className="relative flex gap-3">
            {i < runs.length - 1 && <span aria-hidden className="absolute left-[19px] top-10 h-[calc(100%-1rem)] w-px bg-line" />}
            <div className={`relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ring-1 transition-colors ${visible ? (failed ? 'bg-status-critical/10 ring-status-critical/40' : 'bg-white ring-primary/40') : 'bg-page ring-line'}`}>
              {active ? <Loader2 className="h-4 w-4 animate-spin text-primary" aria-hidden /> : <Icon className={`h-4 w-4 ${visible ? 'text-primary' : 'text-secondary/50'}`} aria-hidden />}
            </div>
            <AnimatePresence>
              {visible && (
                <motion.div initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.3 }} className="min-w-0 flex-1 pb-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-display font-semibold text-heading">{r.agent_name}</span>
                    {failed ? <XCircle className="h-4 w-4 text-status-critical" aria-label="failed" /> : <CheckCircle2 className="h-4 w-4 text-status-resolved" aria-label="completed" />}
                    <span className="muted text-xs">{ms(r.duration_ms)}</span>
                  </div>
                  <p className="mt-0.5 text-sm text-secondary">{summarizeRun(r)}</p>
                </motion.div>
              )}
            </AnimatePresence>
            {!visible && <p className="self-center text-sm text-secondary/60">{r.agent_name}</p>}
          </li>
        )
      })}
    </ol>
  )
}
