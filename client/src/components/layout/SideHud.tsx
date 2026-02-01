import { cn } from "@/lib/utils"

type Item = {
  key: string
  label: string
}

type Props = {
  activeKey: string
  items: Item[]
  onSelect: (key: string) => void
}

export function SideHud({ activeKey, items, onSelect }: Props) {
  return (
    <aside className="hidden lg:block">
      <div className="sticky top-20">
        <div className="w-56 rounded-2xl border border-slate-200 bg-white/80 p-2 shadow-sm backdrop-blur">
          <div className="px-3 pb-2 pt-1 text-xs font-semibold text-slate-500">HUD</div>
          <nav className="space-y-1">
            {items.map((it) => (
              <button
                key={it.key}
                onClick={() => onSelect(it.key)}
                className={cn(
                  "w-full rounded-xl px-3 py-2 text-left text-sm transition-colors",
                  it.key === activeKey
                    ? "bg-indigo-600 text-white"
                    : "text-slate-700 hover:bg-slate-100 hover:text-slate-900"
                )}
              >
                {it.label}
              </button>
            ))}
          </nav>
        </div>
      </div>
    </aside>
  )
}

