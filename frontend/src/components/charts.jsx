import { useState } from 'react'
import { motion } from 'framer-motion'

// Neutral/brand palette for non-status data (categories, teams). Status data uses its own colours via `colorFor`.
const PALETTE = ['#F97316', '#1E293B', '#64748B', '#FDBA74', '#334155', '#EA580C', '#CBD5E1']
const pick = (colorFor, name, i) => (colorFor && colorFor(name)) || PALETTE[i % PALETTE.length]

export function AreaChart({ data, xKey = 'date', yKey = 'tickets', height = 200 }) {
  const [hover, setHover] = useState(null)
  const W = 640, H = height, P = { l: 30, r: 10, t: 12, b: 24 }
  const max = Math.max(1, ...data.map((d) => d[yKey]))
  const x = (i) => P.l + (i * (W - P.l - P.r)) / Math.max(1, data.length - 1)
  const y = (v) => P.t + (1 - v / max) * (H - P.t - P.b)
  const line = data.map((d, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(d[yKey]).toFixed(1)}`).join(' ')
  const area = `${line} L${x(data.length - 1)},${H - P.b} L${x(0)},${H - P.b} Z`
  const ticks = [0, 0.5, 1].map((f) => Math.round(max * f))
  const onMove = (e) => {
    const r = e.currentTarget.getBoundingClientRect()
    const rel = ((e.clientX - r.left) / r.width) * W
    setHover(Math.max(0, Math.min(data.length - 1, Math.round(((rel - P.l) / (W - P.l - P.r)) * (data.length - 1)))))
  }
  const h = hover != null ? data[hover] : null
  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Ticket volume over time" onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
        <defs>
          <linearGradient id="areaFill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#F97316" stopOpacity="0.28" /><stop offset="100%" stopColor="#F97316" stopOpacity="0" />
          </linearGradient>
        </defs>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={P.l} x2={W - P.r} y1={y(t)} y2={y(t)} stroke="#E2E8F0" />
            <text x={P.l - 6} y={y(t) + 4} textAnchor="end" fontSize="10" fill="#64748B">{t}</text>
          </g>
        ))}
        <path d={area} fill="url(#areaFill)" />
        <motion.path d={line} fill="none" stroke="#F97316" strokeWidth="2.4" strokeLinejoin="round" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.9, ease: 'easeOut' }} />
        {data.map((d, i) => (i % Math.ceil(data.length / 7) === 0 ? <text key={d[xKey]} x={x(i)} y={H - 6} textAnchor="middle" fontSize="10" fill="#64748B">{String(d[xKey]).slice(5)}</text> : null))}
        {hover != null && <g><line x1={x(hover)} x2={x(hover)} y1={P.t} y2={H - P.b} stroke="#CBD5E1" /><circle cx={x(hover)} cy={y(h[yKey])} r="4.5" fill="#F97316" stroke="#FFFFFF" strokeWidth="2" /></g>}
      </svg>
      {h && <div className="pointer-events-none absolute right-2 top-0 rounded-lg bg-heading px-2.5 py-1 text-xs text-white shadow-pop">{h[xKey]}: <b>{h[yKey]}</b> tickets</div>}
    </div>
  )
}

export function Donut({ data, size = 150, label, colorFor }) {
  const total = data.reduce((s, d) => s + d.value, 0)
  const R = 52, C = 2 * Math.PI * R
  let acc = 0
  return (
    <div className="flex flex-wrap items-center gap-5">
      <svg width={size} height={size} viewBox="0 0 140 140" role="img" aria-label={label}>
        <circle cx="70" cy="70" r={R} fill="none" stroke="#E2E8F0" strokeWidth="16" />
        {total > 0 && data.map((d, i) => {
          const len = (d.value / total) * C
          const el = (
            <motion.circle key={d.name} cx="70" cy="70" r={R} fill="none" stroke={pick(colorFor, d.name, i)} strokeWidth="16" transform="rotate(-90 70 70)"
              strokeDasharray={`${Math.max(0, len - 2)} ${C}`} strokeDashoffset={-acc} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.06 }} />
          )
          acc += len
          return el
        })}
        <text x="70" y="68" textAnchor="middle" fontSize="22" fontWeight="700" fill="#0F172A" fontFamily="Bricolage Grotesque, sans-serif">{total}</text>
        <text x="70" y="86" textAnchor="middle" fontSize="10" fill="#64748B">tickets</text>
      </svg>
      <ul className="min-w-[8rem] space-y-1.5 text-sm">
        {data.map((d, i) => (
          <li key={d.name} className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full" style={{ background: pick(colorFor, d.name, i) }} /><span className="text-heading">{d.name}</span><span className="ml-auto pl-3 font-semibold text-heading">{d.value}</span></li>
        ))}
      </ul>
    </div>
  )
}

export function BarList({ data, unit = '', color = '#F97316', colorFor }) {
  const max = Math.max(1, ...data.map((d) => d.value))
  return (
    <ul className="space-y-3">
      {data.map((d, i) => (
        <li key={d.name}>
          <div className="mb-1 flex justify-between text-sm"><span className="text-heading">{d.name}</span><span className="font-semibold text-heading">{d.value}{unit}</span></div>
          <div className="h-2 overflow-hidden rounded-full bg-line">
            <motion.div className="h-full rounded-full" style={{ background: (colorFor && colorFor(d.name)) || color }} initial={{ width: 0 }} animate={{ width: `${(d.value / max) * 100}%` }} transition={{ delay: i * 0.05, duration: 0.5 }} />
          </div>
        </li>
      ))}
    </ul>
  )
}

export function ScoreRing({ value = 0, max = 100, size = 96, label, tone = '#F97316' }) {
  const R = 40
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg viewBox="0 0 100 100" width={size} height={size} role="img" aria-label={`${label}: ${value} of ${max}`}>
        <circle cx="50" cy="50" r={R} fill="none" stroke="#E2E8F0" strokeWidth="9" />
        <motion.circle cx="50" cy="50" r={R} fill="none" stroke={tone} strokeWidth="9" strokeLinecap="round" transform="rotate(-90 50 50)"
          initial={{ pathLength: 0 }} animate={{ pathLength: Math.min(1, value / max) }} transition={{ duration: 0.7, ease: 'easeOut' }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-display text-xl font-bold text-heading">{value}</span>
        {label && <span className="text-[10px] text-secondary">{label}</span>}
      </div>
    </div>
  )
}
