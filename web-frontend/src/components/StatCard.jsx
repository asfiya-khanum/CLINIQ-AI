import GlassCard from './GlassCard'

const ACCENT_MAP = {
  cyan: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30',
  blue: 'bg-blue-500/15 text-blue-300 border-blue-500/30',
  amber: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  rose: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
  emerald: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
}

export default function StatCard({ label, value, subtitle, icon: Icon, accent = 'cyan' }) {
  const iconStyle = ACCENT_MAP[accent] || ACCENT_MAP.cyan
  return (
    <GlassCard className="p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            {label}
          </p>
          <p className="mt-2.5 text-3xl font-bold tracking-tight text-white">
            {value}
          </p>
          {subtitle && (
            <p className="mt-1.5 text-xs font-medium text-cyan-300/90">
              {subtitle}
            </p>
          )}
        </div>
        {Icon && (
          <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border ${iconStyle}`}>
            <Icon className="h-5 w-5" />
          </div>
        )}
      </div>
    </GlassCard>
  )
}
