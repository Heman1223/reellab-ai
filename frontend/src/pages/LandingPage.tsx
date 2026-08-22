/**
 * Landing page — the first thing the panel sees.
 *
 * This is a visual statement, not a form. It communicates what ReelLab does
 * in 3 seconds, then gives the user one clear action: Enter the lab.
 */

const FLOW_STEPS = [
  {
    step: '01',
    title: 'Upload Your Reel',
    description: 'Drop in your video. FFmpeg extracts frames and audio in real-time.',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-6 h-6">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
      </svg>
    ),
  },
  {
    step: '02',
    title: 'Gemini Reads It',
    description: 'Multimodal AI extracts hook, scenes, tone, pacing — the Content DNA.',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-6 h-6">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23-.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
      </svg>
    ),
  },
  {
    step: '03',
    title: '10 AI Personas Watch',
    description: 'Each synthetic viewer has unique psychology, attention span, and swiping habits.',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-6 h-6">
        <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" />
      </svg>
    ),
  },
  {
    step: '04',
    title: 'Propagation Modelled',
    description: 'A viral cascade simulation shows how far your reel could actually spread.',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-6 h-6">
        <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
      </svg>
    ),
  },
  {
    step: '05',
    title: 'Get Actionable Results',
    description: 'Drop-off points, bottleneck causes, and counterfactual experiments — before you publish.',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-6 h-6">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
      </svg>
    ),
  },
];

const STATS = [
  { value: '10', label: 'AI Personas', sub: 'per simulation' },
  { value: '5', label: 'Analysis Stages', sub: 'fully automated' },
  { value: '∞', label: 'Experiments', sub: 'before publishing' },
];

export default function LandingPage() {
  return (
    <div className="relative overflow-hidden">
      {/* ── Background decorations ─────────────────────────────────── */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 overflow-hidden"
        style={{ zIndex: 0 }}
      >
        {/* Top-right glow */}
        <div
          className="absolute -right-40 -top-40 h-[600px] w-[600px] rounded-full opacity-20"
          style={{
            background: 'radial-gradient(circle, #d75d4e 0%, transparent 70%)',
            filter: 'blur(60px)',
          }}
        />
        {/* Bottom-left glow */}
        <div
          className="absolute -bottom-40 -left-40 h-[500px] w-[500px] rounded-full opacity-10"
          style={{
            background: 'radial-gradient(circle, #6366f1 0%, transparent 70%)',
            filter: 'blur(80px)',
          }}
        />
        {/* Grid overlay */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage:
              'linear-gradient(#000 1px, transparent 1px), linear-gradient(90deg, #000 1px, transparent 1px)',
            backgroundSize: '40px 40px',
          }}
        />
      </div>

      {/* ── Hero ────────────────────────────────────────────────────── */}
      <div
        className="relative z-10 flex flex-col items-center justify-center min-h-[88vh] text-center px-4 pt-8 pb-16"
      >
        {/* Badge */}
        <div className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/5 px-4 py-1.5 text-[11px] font-bold tracking-[0.18em] text-accent uppercase mb-8">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-accent" />
          </span>
          Experiment Before You Publish
        </div>

        {/* Headline */}
        <h1 className="text-5xl md:text-7xl lg:text-8xl font-serif font-bold tracking-tight text-slate-900 mb-6 w-full leading-[1.05]">
          <span
            className="inline-block pb-2"
            style={{
              background: 'linear-gradient(135deg, #d75d4e 0%, #8b5cf6 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}
          >
            Experiment Before You Publish
          </span>
        </h1>

        {/* Sub-headline */}
        <p className="text-lg md:text-xl text-slate-500 max-w-2xl mb-12 leading-relaxed font-sans mx-auto">
          ReelLab spawns{' '}
          <span className="font-semibold text-slate-700">10 autonomous AI viewers</span>
          , each with distinct psychology and swiping habits, and simulates them watching your Reel
          — before you touch publish.
        </p>

        {/* Animated Flow Diagram */}
        <div className="flex flex-wrap items-center justify-center gap-2 md:gap-4 mb-16 max-w-4xl mx-auto w-full px-4 overflow-hidden">
          {[
            { label: 'Reel', icon: 'M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5' },
            { label: 'AI understands', icon: 'M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23-.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5' },
            { label: '10 viewers', icon: 'M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z' },
            { label: 'Results', icon: 'M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5' },
            { label: 'Insights', icon: 'M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z' }
          ].map((node, i, arr) => (
            <div key={node.label} className="flex items-center gap-2 md:gap-4">
              <div
                className="flex flex-col items-center gap-2 group animate-in slide-in-from-bottom-4 fade-in duration-700"
                style={{ animationDelay: `${i * 200}ms`, animationFillMode: 'both' }}
              >
                <div className="flex h-14 w-14 md:h-16 md:w-16 items-center justify-center rounded-2xl bg-white border border-ink-600 shadow-md group-hover:border-accent/50 group-hover:shadow-lg transition-all duration-300">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-6 h-6 md:w-7 md:h-7 text-slate-700 group-hover:text-accent transition-colors">
                    <path strokeLinecap="round" strokeLinejoin="round" d={node.icon} />
                  </svg>
                </div>
                <span className="text-[10px] md:text-xs font-semibold uppercase tracking-wider text-slate-500 whitespace-nowrap">
                  {node.label}
                </span>
              </div>
              {i < arr.length - 1 && (
                <div className="flex-shrink-0 animate-in fade-in duration-700" style={{ animationDelay: `${(i * 200) + 100}ms`, animationFillMode: 'both' }}>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-5 h-5 text-ink-600">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                  </svg>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Stats row */}
        <div className="flex items-center gap-8 md:gap-16 mb-12">
          {STATS.map((stat) => (
            <div key={stat.label} className="text-center">
              <div
                className="text-3xl md:text-4xl font-black text-slate-900 font-serif"
                style={{
                  background: 'linear-gradient(135deg, #d75d4e, #8b5cf6)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text',
                }}
              >
                {stat.value}
              </div>
              <div className="text-xs font-bold uppercase tracking-wider text-slate-700 mt-0.5">
                {stat.label}
              </div>
              <div className="text-[10px] text-slate-400">{stat.sub}</div>
            </div>
          ))}
        </div>

        {/* CTA */}
        <button
          onClick={() => document.getElementById('upload')?.scrollIntoView({ behavior: 'smooth' })}
          className="group relative inline-flex items-center gap-3 px-10 py-4 text-base font-semibold rounded-full shadow-xl transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 active:translate-y-0"
          style={{
            background: 'linear-gradient(135deg, #d75d4e 0%, #b94a3c 100%)',
            color: '#fff',
            boxShadow: '0 8px 32px rgba(215,93,78,0.35)',
          }}
        >
          <span>Enter the Simulation Lab</span>
          <svg
            viewBox="0 0 20 20"
            fill="currentColor"
            className="w-4 h-4 transition-transform group-hover:translate-x-1"
          >
            <path
              fillRule="evenodd"
              d="M3 10a.75.75 0 01.75-.75h10.638L10.23 5.29a.75.75 0 111.04-1.08l5.5 5.25a.75.75 0 010 1.08l-5.5 5.25a.75.75 0 11-1.04-1.08l4.158-3.96H3.75A.75.75 0 013 10z"
              clipRule="evenodd"
            />
          </svg>
        </button>

        {/* Scroll hint */}
        <p className="mt-6 text-xs text-slate-400 tracking-wider uppercase">
          No account. No data stored. Just the simulation.
        </p>
      </div>

      {/* ── How it works ─────────────────────────────────────────────── */}
      <div className="relative z-10 py-20 px-4 border-t border-ink-700">
        <div className="mx-auto max-w-screen-xl">
          <div className="text-center mb-14">
            <div className="text-[10px] font-bold tracking-[0.2em] text-accent uppercase mb-3">
              The Pipeline
            </div>
            <h2 className="text-3xl md:text-4xl font-serif font-bold text-slate-900">
              From upload to insight in 5 automated stages
            </h2>
          </div>

          {/* Step cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            {FLOW_STEPS.map((item, idx) => (
              <div
                key={item.step}
                className="relative group rounded-2xl border border-ink-700 bg-white p-5 shadow-sm hover:shadow-lg hover:-translate-y-1 transition-all duration-300"
              >
                {/* Step connector line (desktop) */}
                {idx < FLOW_STEPS.length - 1 && (
                  <div
                    aria-hidden="true"
                    className="hidden lg:block absolute top-8 right-0 w-4 h-px bg-ink-700 translate-x-4 z-10"
                  />
                )}

                {/* Step number */}
                <div className="text-[10px] font-bold tracking-[0.15em] text-slate-300 uppercase mb-3">
                  {item.step}
                </div>

                {/* Icon */}
                <div
                  className="mb-3 inline-flex items-center justify-center h-10 w-10 rounded-xl text-accent"
                  style={{ background: 'rgba(215,93,78,0.08)' }}
                >
                  {item.icon}
                </div>

                {/* Content */}
                <h3 className="font-bold text-slate-900 text-sm mb-1.5 font-serif">{item.title}</h3>
                <p className="text-xs text-slate-500 leading-relaxed">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Why it's different ───────────────────────────────────────── */}
      <div className="relative z-10 py-16 px-4 border-t border-ink-700">
        <div className="mx-auto max-w-3xl text-center">
          <div className="text-[10px] font-bold tracking-[0.2em] text-accent uppercase mb-3">
            Not a score. A simulation.
          </div>
          <h2 className="text-2xl md:text-3xl font-serif font-bold text-slate-900 mb-6">
            Generic virality scores tell you nothing.<br />
            ReelLab tells you <em>why</em>.
          </h2>
          <p className="text-slate-500 text-base leading-relaxed mb-10">
            Every persona has an attention span, a reason to leave, a set of things they genuinely care about.
            When they watch your reel, they tell you exactly where you lost them — in their own words.
            Then you fix it and re-run before you ever touch publish.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-left">
            {[
              {
                title: 'Pinpoint drop-off',
                body: 'See the exact second viewers lose interest and read their first-person reasoning.',
                color: '#d75d4e',
              },
              {
                title: 'Viral cascade',
                body: 'Propagation simulation models how far your reel could actually spread across segments.',
                color: '#8b5cf6',
              },
              {
                title: 'Counterfactual lab',
                body: 'Change one lever — hook, tone, CTA — and re-simulate. Know the ROI before editing.',
                color: '#10b981',
              },
            ].map((card) => (
              <div
                key={card.title}
                className="rounded-2xl border border-ink-700 bg-white p-5 shadow-sm"
              >
                <div
                  className="mb-3 h-1 w-8 rounded-full"
                  style={{ background: card.color }}
                />
                <h3 className="font-bold text-slate-900 text-sm mb-1.5">{card.title}</h3>
                <p className="text-xs text-slate-500 leading-relaxed">{card.body}</p>
              </div>
            ))}
          </div>

          <button
            onClick={() => document.getElementById('upload')?.scrollIntoView({ behavior: 'smooth' })}
            className="mt-10 inline-flex items-center gap-2 text-sm font-semibold text-accent hover:underline underline-offset-2 transition-all"
          >
            Upload your first reel
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path
                fillRule="evenodd"
                d="M10 3a.75.75 0 01.75.75v10.638l3.96-4.158a.75.75 0 111.08 1.04l-5.25 5.5a.75.75 0 01-1.08 0l-5.25-5.5a.75.75 0 111.08-1.04l3.96 4.158V3.75A.75.75 0 0110 3z"
                clipRule="evenodd"
                transform="rotate(270, 10, 10)"
              />
              <path
                fillRule="evenodd"
                d="M3 10a.75.75 0 01.75-.75h10.638L10.23 5.29a.75.75 0 111.04-1.08l5.5 5.25a.75.75 0 010 1.08l-5.5 5.25a.75.75 0 11-1.04-1.08l4.158-3.96H3.75A.75.75 0 013 10z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
