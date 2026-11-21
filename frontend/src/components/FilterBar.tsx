import { PlatformMark } from './ui/PlatformMark'
import { Segmented } from './ui/primitives'
import { useFilters } from '../hooks/useFilters'
import { PLATFORM_IDS, PLATFORM_LABEL } from '../types/api'
import clsx from 'clsx'

export function FilterBar({ hideRange }: { hideRange?: boolean }) {
  const f = useFilters()
  return (
    <div className="flex flex-wrap items-center gap-3">
      {!hideRange && <Segmented value={f.days} onChange={f.setDays} options={[{ value: 7, label: '7d' }, { value: 30, label: '30d' }, { value: 90, label: '90d' }, { value: 180, label: '6mo' }]} />}
      <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Platform filter">
        <button onClick={f.clearPlatforms} className={clsx('rounded-full border px-3 py-1.5 text-[13px] transition-colors', f.platforms.length === 0 ? 'border-cyan/50 bg-cyan/10 text-cyan' : 'border-line text-muted hover:text-ink')}>All</button>
        {PLATFORM_IDS.map((p) => {
          const on = f.platforms.includes(p)
          return (
            <button key={p} onClick={() => f.togglePlatform(p)} aria-pressed={on} title={PLATFORM_LABEL[p]}
              className={clsx('flex items-center gap-1.5 rounded-full border px-2.5 py-1.5 text-[13px] transition-colors', on ? 'border-cyan/50 bg-cyan/10 text-ink' : 'border-line text-muted hover:text-ink')}>
              <PlatformMark platform={p} size={15} /><span className="hidden sm:inline">{PLATFORM_LABEL[p]}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
