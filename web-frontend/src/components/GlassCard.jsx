export default function GlassCard({ children, className = '', hover = true }) {
  return (
    <div
      className={`rounded-2xl border border-slate-800/80 bg-[#0D1528]/80 backdrop-blur-xl shadow-[0_10px_35px_rgba(0,0,0,0.35)] ${
        hover
          ? 'transition-all duration-300 hover:-translate-y-0.5 hover:border-cyan-500/40 hover:shadow-[0_14px_40px_rgba(6,182,212,0.12)]'
          : ''
      } ${className}`}
    >
      {children}
    </div>
  )
}
