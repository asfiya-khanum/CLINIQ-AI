const TONE_MAP = {
  normal: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  consistent: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  review_recommended: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  review: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  attention_needed: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
  high: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
  info: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30',
  demo: 'bg-blue-500/15 text-blue-300 border-blue-500/30',
}

export default function StatusBadge({ label, tone = 'info', className = '' }) {
  const styles = TONE_MAP[tone] || TONE_MAP.info
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold tracking-wide ${styles} ${className}`}
    >
      {label}
    </span>
  )
}
