export function DashboardPage() {
  return (
    <div className="space-y-12">
      <section className="pt-4">
        <div className="mx-auto max-w-4xl text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-100 bg-indigo-50 px-4 py-2 text-xs font-medium text-indigo-700">
            <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-indigo-600 text-[10px] text-white">✦</span>
            设计师专用的生成式 AI 引擎 V2.1
          </div>

          <h1 className="mt-8 text-5xl font-semibold leading-[1.05] tracking-tight text-slate-900">
            从手稿到
            <span className="mx-2 bg-gradient-to-r from-indigo-500 to-violet-500 bg-clip-text text-transparent">全真设计落地</span>,
            仅需一瞬
          </h1>

          <p className="mx-auto mt-6 max-w-2xl text-base leading-7 text-slate-600">
            Structura AI 升级支持室内、景观与平面海报三大领域。严格遵循专业规范，让 AI 真正成为懂施工、懂生态、懂营销的设计助理。
          </p>

          <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <a
              href="/app/workshop"
              className="inline-flex h-11 items-center justify-center rounded-xl bg-indigo-600 px-6 text-sm font-medium text-white shadow-sm shadow-indigo-200 transition-colors hover:bg-indigo-700"
            >
              开始设计 <span className="ml-2">→</span>
            </a>
            <a
              href="/app/interior?mode=interior"
              className="inline-flex h-11 items-center justify-center rounded-xl border border-slate-200 bg-white px-6 text-sm font-medium text-slate-900 shadow-sm transition-colors hover:bg-slate-50"
            >
              查看演示案例
            </a>
          </div>
        </div>
      </section>

      <section className="pb-10">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
              <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4 4 8v8l8 4 8-4V8l-8-4Z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 8l8 4 8-4" />
              </svg>
            </div>
            <div className="mt-5 text-lg font-semibold text-slate-900">多维空间引擎</div>
            <div className="mt-2 text-sm leading-6 text-slate-600">室内、景观、平面三大模型，针对不同设计场景智能切换底层算法与约束条件。</div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
              <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 7a3 3 0 0 1 3-3h10a3 3 0 0 1 3 3v10a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V7Z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M8 9h8M8 13h8M8 17h5" />
              </svg>
            </div>
            <div className="mt-5 text-lg font-semibold text-slate-900">专业知识图谱</div>
            <div className="mt-2 text-sm leading-6 text-slate-600">内置植物配置表、室内施工规范及广告法规视觉库，确保设计既美观又合规。</div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
              <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M7 8h10M7 12h6M7 16h10" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 20h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2Z" />
              </svg>
            </div>
            <div className="mt-5 text-lg font-semibold text-slate-900">自然语言精修</div>
            <div className="mt-2 text-sm leading-6 text-slate-600">生成结果不满意？直接像聊天一样告诉 AI：“把草坪换成碎石铺地”。</div>
          </div>
        </div>
      </section>
    </div>
  )
}

