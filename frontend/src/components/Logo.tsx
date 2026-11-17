import { Link } from 'react-router-dom'

export function Logo({ compact, to = '/' }: { compact?: boolean; to?: string }) {
  return (
    <Link to={to} className="inline-flex items-center gap-2.5" aria-label="SocialIQ home">
      <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden><rect width="32" height="32" rx="9" fill="#10151C" stroke="#24303D" /><path d="M6 21l5-6 4 3 5-8 6 7" fill="none" stroke="#22D3EE" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" /><circle cx="26" cy="12" r="2.2" fill="#34D399" /></svg>
      {!compact && <span className="text-[17px] font-semibold tracking-tight">Social<span className="text-gradient">IQ</span></span>}
    </Link>
  )
}
