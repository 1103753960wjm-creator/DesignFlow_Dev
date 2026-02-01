import { Link } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

type Props = {
  active: "home" | "workshop" | "knowledge"
  userLabel?: string
  onLogout: () => void
}

function SettingsIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.75">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Zm8.1-3.5a8.2 8.2 0 0 0-.1-1l2-1.6-2-3.4-2.4 1a8.2 8.2 0 0 0-1.7-1l-.4-2.6H10.5L10 6a8.2 8.2 0 0 0-1.7 1l-2.4-1-2 3.4 2 1.6a8.2 8.2 0 0 0 0 2l-2 1.6 2 3.4 2.4-1a8.2 8.2 0 0 0 1.7 1l.5 2.6h4l.5-2.6a8.2 8.2 0 0 0 1.7-1l2.4 1 2-3.4-2-1.6c.1-.3.1-.7.1-1Z"
      />
    </svg>
  )
}

export function TopNav({ active, userLabel, onLogout }: Props) {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link to="/app" className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-indigo-200 bg-indigo-50 text-indigo-600">
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 3 4 7.5v9L12 21l8-4.5v-9L12 3Z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v18" />
            </svg>
          </div>
          <div className="text-base font-semibold text-slate-900">Structura.AI</div>
        </Link>

        <nav className="hidden items-center gap-8 text-sm md:flex">
          <Link
            to="/app"
            className={cn("font-medium text-slate-600 hover:text-slate-900", active === "home" && "text-indigo-600")}
          >
            首页
          </Link>
          <Link
            to="/app/workshop"
            className={cn(
              "font-medium text-slate-600 hover:text-slate-900",
              active === "workshop" && "text-indigo-600"
            )}
          >
            设计工坊
          </Link>
          <Link
            to="/app/knowledge"
            className={cn(
              "font-medium text-slate-600 hover:text-slate-900",
              active === "knowledge" && "text-indigo-600"
            )}
          >
            专业知识库
          </Link>
        </nav>

        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" aria-label="设置">
            <SettingsIcon />
          </Button>
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-600 text-xs font-semibold text-white">
            {userLabel ?? "DE"}
          </div>
          <Button variant="ghost" onClick={onLogout}>
            退出
          </Button>
        </div>
      </div>
    </header>
  )
}

