import {
  Search,
  Zap,
  ShieldCheck,
  Database,
  Clock,
  FolderCheck,
  FileText,
  Layers,
  BookOpen,
  StickyNote,
  Package,
  ChevronRight,
  CheckCircle2,
  ArrowRight,
  Loader2,
} from "lucide-react";
import type { AlexandriaDashboardData } from "../hooks/useAlexandriaHooks";

interface DashboardProps {
  mode: "simple" | "advanced";
  setMode: (mode: "simple" | "advanced") => void;
  data: AlexandriaDashboardData;
  query: string;
  setQuery: (query: string) => void;
  runPacket: (query?: string) => void;
  seedDogfoodMemory: () => void;
  isRunning: boolean;
}

export default function Dashboard({
  mode,
  setMode,
  data,
  query,
  setQuery,
  runPacket,
  seedDogfoodMemory,
  isRunning,
}: DashboardProps) {
  return (
    <div className="space-y-4">
      {/* Mode toggle */}
      <div className="inline-flex rounded-lg border border-mist bg-white p-1">
        <button
          onClick={() => setMode("simple")}
          className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
            mode === "simple" ? "bg-ink text-white" : "text-ink-secondary hover:bg-ivory"
          }`}
        >
          Simple Mode
        </button>
        <button
          onClick={() => setMode("advanced")}
          className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
            mode === "advanced" ? "bg-ink text-white" : "text-ink-secondary hover:bg-ivory"
          }`}
        >
          Advanced Mode
        </button>
      </div>

      {mode === "simple" ? (
        <SimpleDashboard query={query} setQuery={setQuery} runPacket={runPacket} isRunning={isRunning} />
      ) : (
        <AdvancedDashboard
          data={data}
          query={query}
          setQuery={setQuery}
          runPacket={runPacket}
          seedDogfoodMemory={seedDogfoodMemory}
          isRunning={isRunning}
        />
      )}
    </div>
  );
}

function SimpleDashboard({
  query,
  setQuery,
  runPacket,
  isRunning,
}: {
  query: string;
  setQuery: (query: string) => void;
  runPacket: (query?: string) => void;
  isRunning: boolean;
}) {
  return (
    <div className="rounded-lg border border-mist bg-white p-6 space-y-6">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-full bg-ivory flex items-center justify-center">
          <Search className="h-5 w-5 text-ink" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-ink">Ask Alexandria</h3>
          <p className="text-sm text-ink-secondary">Type a question or task to get started</p>
        </div>
      </div>
      <form
        className="flex items-center gap-2 rounded-lg border border-mist bg-ivory px-4 py-3"
        onSubmit={(event) => {
          event.preventDefault();
          runPacket(query);
        }}
      >
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          className="min-w-0 flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-ink-secondary/60"
          placeholder="Ask a question or give an agent task"
        />
        <button
          type="submit"
          className="inline-flex h-8 w-8 items-center justify-center rounded-md bg-ink text-white hover:bg-graphite disabled:opacity-60"
          disabled={isRunning}
          aria-label="Build context packet"
        >
          {isRunning ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
        </button>
      </form>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {[
          { label: "Recall", desc: "Find relevant memory" },
          { label: "Build packet", desc: "Assemble context" },
          { label: "Verify", desc: "Review & approve" },
        ].map((s) => (
          <div key={s.label} className="rounded-lg border border-mist bg-white p-3">
            <p className="text-sm font-semibold text-ink">{s.label}</p>
            <p className="text-xs text-ink-secondary mt-0.5">{s.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function AdvancedDashboard({
  data,
  query,
  setQuery,
  runPacket,
  seedDogfoodMemory,
  isRunning,
}: {
  data: AlexandriaDashboardData;
  query: string;
  setQuery: (query: string) => void;
  runPacket: (query?: string) => void;
  seedDogfoodMemory: () => void;
  isRunning: boolean;
}) {
  return (
    <div className="space-y-4">
      {/* 1. Command Panel */}
      <div className="rounded-lg border border-mist bg-white p-4">
        <label className="text-xs font-semibold text-ink-secondary uppercase tracking-wide">Command</label>
        <form
          className="mt-2 flex items-center gap-2 rounded-lg border border-mist bg-ivory px-4 py-3"
          onSubmit={(event) => {
            event.preventDefault();
            runPacket(query);
          }}
        >
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="min-w-0 flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-ink-secondary/60"
            placeholder="Ask anything or give an agent task"
          />
          <button
            type="submit"
            className="inline-flex h-8 w-8 items-center justify-center rounded-md bg-ink text-white hover:bg-graphite disabled:opacity-60"
            disabled={isRunning}
            aria-label="Build context packet"
          >
            {isRunning ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
          </button>
        </form>
        <div className="mt-3 flex flex-wrap gap-2">
          {data.commandChips.map((chip) => (
            <button
              key={chip}
              onClick={() => runPacket(chip)}
              className="rounded-full border border-mist bg-white px-3 py-1 text-xs font-medium text-ink-secondary hover:border-amber hover:text-amber transition-colors"
            >
              {chip}
            </button>
          ))}
        </div>
        {data.error && <p className="mt-3 text-xs font-medium text-warning">{data.error}</p>}
        {data.actionMessage && <p className="mt-3 text-xs font-medium text-success">{data.actionMessage}</p>}
        {data.connection === "online" && data.memoryOverview.total === 0 && (
          <div className="mt-3 rounded-lg border border-amber bg-amber/5 p-3">
            <p className="text-xs font-semibold text-ink">No memory is loaded yet.</p>
            <p className="mt-1 text-xs text-ink-secondary">
              Load a small Alexandria/D-ACCA dogfood seed so packet generation, proof, sources, and feedback are testable.
            </p>
            <button
              onClick={seedDogfoodMemory}
              disabled={isRunning}
              className="mt-3 inline-flex items-center gap-1 rounded-md bg-ink px-3 py-1.5 text-xs font-medium text-white hover:bg-graphite disabled:opacity-60"
            >
              {isRunning && <Loader2 className="h-3 w-3 animate-spin" />}
              Load dogfood memory
            </button>
          </div>
        )}
      </div>

      {/* 2. Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <MetricCard icon={<Package className="h-4 w-4" />} label="Admissible packet" value={data.metrics.admissiblePacket} />
        <MetricCard icon={<ShieldCheck className="h-4 w-4" />} label="Confidence" value={`${data.metrics.confidence}%`} />
        <MetricCard icon={<Zap className="h-4 w-4" />} label="Fresh items" value={`${data.metrics.freshItems.toLocaleString()}`} />
        <MetricCard icon={<Clock className="h-4 w-4" />} label="Stale items" value={`${data.metrics.staleItems.toLocaleString()}`} />
        <MetricCard icon={<FolderCheck className="h-4 w-4" />} label="Trusted sources" value={`${data.metrics.trustedSources.toLocaleString()}`} />
      </div>

      {/* 3. Memory Overview */}
      <div className="rounded-lg border border-mist bg-white p-4">
        <h3 className="text-sm font-semibold text-ink">Memory Overview</h3>
        <div className="mt-3 grid grid-cols-3 md:grid-cols-6 gap-3">
          <StatItem icon={<BookOpen className="h-4 w-4" />} label="Preferences" value={`${data.memoryOverview.preferences}`} />
          <StatItem icon={<Layers className="h-4 w-4" />} label="Aliases" value={`${data.memoryOverview.aliases}`} />
          <StatItem icon={<FolderCheck className="h-4 w-4" />} label="Projects" value={`${data.memoryOverview.projects}`} />
          <StatItem icon={<ShieldCheck className="h-4 w-4" />} label="Policies" value={`${data.memoryOverview.policies}`} />
          <StatItem icon={<StickyNote className="h-4 w-4" />} label="Notes" value={`${data.memoryOverview.notes.toLocaleString()}`} />
          <StatItem icon={<Database className="h-4 w-4" />} label="Total" value={`${data.memoryOverview.total.toLocaleString()}`} highlight />
        </div>
      </div>

      {/* 4. Context Packet Preview */}
      <div className="rounded-lg border border-mist bg-white p-4">
        <h3 className="text-sm font-semibold text-ink">Context Packet Preview</h3>
        <div className="mt-3 space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-ink-secondary">Current objective</span>
            <span className="font-medium text-ink text-right">{data.contextPacket.objective}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-ink-secondary">Relevant memory</span>
            <span className="font-medium text-ink">{data.contextPacket.relevantMemory} items</span>
          </div>
          <div className="flex justify-between">
            <span className="text-ink-secondary">Trusted sources</span>
            <span className="font-medium text-ink">{data.contextPacket.trustedSources} items</span>
          </div>
          <div className="flex justify-between">
            <span className="text-ink-secondary">Policy constraints</span>
            <span className="font-medium text-ink">{data.contextPacket.policyConstraints} items</span>
          </div>
        </div>
        <button className="mt-4 inline-flex items-center gap-1 rounded-md bg-ink px-3 py-1.5 text-xs font-medium text-white hover:bg-graphite transition-colors">
          Open Context <ChevronRight className="h-3 w-3" />
        </button>
      </div>

      {/* 5. Route Proof (D-ACCA) */}
      <div className="rounded-lg border border-mist bg-white p-4">
        <h3 className="text-sm font-semibold text-ink">Route Proof (D-ACCA)</h3>
        <div className="mt-3 relative">
          <div className="absolute left-2 top-2 bottom-2 w-px bg-mist" />
          <div className="space-y-4">
            {data.routeProof.map((step, i) => (
              <div key={step.stage} className="relative flex items-start gap-3 pl-6">
                <div className="absolute left-0 top-1 h-4 w-4 rounded-full border-2 border-white bg-amber flex items-center justify-center">
                  {i === data.routeProof.length - 1 ? (
                    <CheckCircle2 className="h-3 w-3 text-white" />
                  ) : (
                    <div className="h-1.5 w-1.5 rounded-full bg-white" />
                  )}
                </div>
                <div>
                  <p className="text-sm font-medium text-ink">
                    {step.stage} <ArrowRight className="inline h-3 w-3 text-mist mx-0.5" /> {step.label}
                  </p>
                  {step.detail && (
                    <p className="text-xs text-ink-secondary mt-0.5">{step.detail}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 6. Sources Provenance */}
      <div className="rounded-lg border border-mist bg-white p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-ink">Sources Provenance</h3>
        </div>
        <div className="mt-3 space-y-2">
          {data.sources.map((s, index) => (
            <div key={`${s.name}-${s.type}-${index}`} className="flex items-center gap-3 rounded-md border border-mist-light px-3 py-2">
              <FileText className="h-4 w-4 text-ink-secondary shrink-0" />
              <span className="text-sm font-medium text-ink flex-1 truncate">{s.name}</span>
              <span className="text-xs text-ink-secondary hidden sm:inline">{s.type}</span>
              <span className="text-xs font-medium text-success bg-success-bg px-2 py-0.5 rounded-full">{s.status}</span>
              <span className="text-xs text-ink-secondary hidden md:inline w-16 text-right">{s.time}</span>
            </div>
          ))}
        </div>
        <button className="mt-3 text-xs font-medium text-amber hover:text-amber-muted transition-colors">
          View all sources
        </button>
      </div>

      {/* 7. Recent Recall Activity */}
      <div className="rounded-lg border border-mist bg-white p-4">
        <h3 className="text-sm font-semibold text-ink">Recent Recall Activity</h3>
        <div className="mt-3 flex gap-3 overflow-x-auto pb-1">
          {data.recallActivity.map((item) => (
            <div
              key={item.detail}
              className="min-w-[220px] max-w-[260px] rounded-md border border-mist-light bg-ivory p-3 shrink-0"
            >
              <p className="text-xs font-medium text-amber">{item.action}</p>
              <p className="text-sm text-ink mt-1 leading-snug">{item.detail}</p>
              <p className="text-xs text-ink-secondary mt-2">{item.time}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function MetricCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-mist bg-white p-3">
      <div className="flex items-center gap-1.5 text-ink-secondary">
        {icon}
        <span className="text-[11px] font-medium uppercase tracking-wide">{label}</span>
      </div>
      <p className="mt-1.5 text-lg font-semibold text-ink">{value}</p>
    </div>
  );
}

function StatItem({
  icon,
  label,
  value,
  highlight,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className={`rounded-md border p-2.5 ${highlight ? "border-amber bg-amber/5" : "border-mist-light bg-ivory"}`}>
      <div className="flex items-center gap-1 text-ink-secondary">
        {icon}
        <span className="text-[11px] font-medium">{label}</span>
      </div>
      <p className={`mt-1 text-base font-semibold ${highlight ? "text-amber" : "text-ink"}`}>{value}</p>
    </div>
  );
}
