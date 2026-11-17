import type { PlatformId } from '../../types/api'

/** Platform identity glyphs. Brand colours appear ONLY here, nowhere else in the UI. */
export function PlatformMark({ platform, size = 20 }: { platform: PlatformId; size?: number }) {
  const s = { width: size, height: size }
  switch (platform) {
    case 'youtube':
      return (<svg {...s} viewBox="0 0 24 24" aria-label="YouTube"><rect x="1" y="4.5" width="22" height="15" rx="4.5" fill="#FF0033" /><path d="M10 9l5 3-5 3z" fill="#fff" /></svg>)
    case 'instagram':
      return (<svg {...s} viewBox="0 0 24 24" aria-label="Instagram"><defs><linearGradient id="ig" x1="0" y1="1" x2="1" y2="0"><stop offset="0" stopColor="#FEDA75" /><stop offset=".35" stopColor="#FA7E1E" /><stop offset=".6" stopColor="#D62976" /><stop offset="1" stopColor="#4F5BD5" /></linearGradient></defs><rect x="2" y="2" width="20" height="20" rx="6" fill="url(#ig)" /><circle cx="12" cy="12" r="4.2" fill="none" stroke="#fff" strokeWidth="1.8" /><circle cx="17.2" cy="6.8" r="1.2" fill="#fff" /></svg>)
    case 'x':
      return (<svg {...s} viewBox="0 0 24 24" aria-label="X"><rect x="1.5" y="1.5" width="21" height="21" rx="6" fill="#000" stroke="#3a4552" /><path d="M7 7l10 10M17 7L7 17" stroke="#fff" strokeWidth="1.9" strokeLinecap="round" /></svg>)
    case 'linkedin':
      return (<svg {...s} viewBox="0 0 24 24" aria-label="LinkedIn"><rect x="2" y="2" width="20" height="20" rx="4.5" fill="#0A66C2" /><path d="M7.2 10v6.6M7.2 7.2v.1M10.6 16.6V10m0 2.6c0-1.6 1-2.7 2.4-2.7s2.2 1 2.2 2.7v4" stroke="#fff" strokeWidth="1.7" strokeLinecap="round" fill="none" /></svg>)
  }
}
