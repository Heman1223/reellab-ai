export default function LandingPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[75vh] text-center px-4">
      <div className="text-[10px] font-bold tracking-[0.2em] text-accent uppercase mb-6">
        The Creator's unfair advantage
      </div>

      <h1 className="text-5xl md:text-7xl font-serif font-bold tracking-tight text-slate-900 mb-8 w-full leading-tight">
        Test-fly your Reels before publishing.
      </h1>
      
      <p className="text-2xl text-slate-600 max-w-4xl mb-16 leading-relaxed font-serif mx-auto">
        Existing predictors just give you a generic "virality score." 
        <br/><br/>
        We do something different: we spawn <strong>dozens of autonomous AI agents</strong>—each with unique attention spans, interests, and personalities—and simulate them watching your Reel in real-time.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16 text-left w-full px-4 lg:px-0">
        <div className="bg-white p-6 rounded-xl border border-ink-600 shadow-sm transition-transform hover:-translate-y-1">
          <h3 className="font-bold text-slate-900 mb-2 font-serif text-lg">Hyper-Targeted Personas</h3>
          <p className="text-sm text-slate-500">Our agents represent specific sub-niches, from "Budget Home Trainees" to "College Gym Starters," replicating real human swiping behavior.</p>
        </div>
        <div className="bg-white p-6 rounded-xl border border-ink-600 shadow-sm transition-transform hover:-translate-y-1">
          <h3 className="font-bold text-slate-900 mb-2 font-serif text-lg">Pinpoint the Drop-off</h3>
          <p className="text-sm text-slate-500">Stop guessing why your Reel tanked. See the exact second viewers lost interest and read their simulated thought processes.</p>
        </div>
        <div className="bg-white p-6 rounded-xl border border-ink-600 shadow-sm transition-transform hover:-translate-y-1">
          <h3 className="font-bold text-slate-900 mb-2 font-serif text-lg">Counterfactual Testing</h3>
          <p className="text-sm text-slate-500">Tweak your hook or pacing and re-run the simulation. Know for a fact that your edit improves retention before uploading to Instagram.</p>
        </div>
      </div>

      <button 
        onClick={() => document.getElementById('upload')?.scrollIntoView({ behavior: 'smooth' })}
        className="px-10 py-4 text-lg font-semibold rounded-full shadow-lg bg-accent text-white hover:bg-accent-soft transition-all hover:shadow-accent/30"
      >
        Enter the Simulation Lab
      </button>
    </div>
  );
}
