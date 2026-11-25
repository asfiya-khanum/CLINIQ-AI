import StatusBadge from './StatusBadge'

export default function PageHeader({
  title,
  subtitle,
  badge = 'Fictional UI Shell • API Integration Pending',
  badgeTone = 'demo',
  actions = null,
}) {
  return (
    <div className="mb-6 flex flex-col gap-4 border-b border-slate-800/80 pb-5 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
            {title}
          </h1>
          {badge && <StatusBadge label={badge} tone={badgeTone} />}
        </div>
        {subtitle && (
          <p className="mt-1.5 max-w-3xl text-sm text-slate-400">
            {subtitle}
          </p>
        )}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2.5">{actions}</div>}
    </div>
  )
}
