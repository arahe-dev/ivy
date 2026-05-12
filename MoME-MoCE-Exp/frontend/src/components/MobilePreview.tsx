import {
  Menu,
  Search,
  CheckCircle2,
  ArrowRight,
  FileText,
  ThumbsUp,
  ThumbsDown,
  AlertTriangle,
} from "lucide-react";
import type { AlexandriaDashboardData } from "../hooks/useAlexandriaHooks";

export default function MobilePreview({
  data,
  sendFeedback,
}: {
  data: AlexandriaDashboardData;
  sendFeedback: (rating: "useful" | "wrong" | "stale" | "missed" | "private" | "neutral", note?: string) => Promise<void>;
}) {
  return (
    <div className="hidden xl:flex justify-center items-start pt-2">
      <div className="relative w-[280px] h-[580px] rounded-[36px] border-[6px] border-graphite bg-graphite shadow-xl overflow-hidden">
        {/* Notch */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 h-5 w-24 rounded-b-xl bg-graphite z-10" />

        {/* Screen */}
        <div className="h-full w-full rounded-[30px] bg-ivory overflow-y-auto p-3 space-y-3">
          {/* Header */}
          <div className="flex items-center justify-between pt-3">
            <img
              src="/assets/alexandria/svg/alexandria-wordmark-primary.svg"
              onError={(e) => {
                const img = e.currentTarget;
                img.src = "/assets/alexandria/png/alexandria-wordmark-primary.png";
                img.onerror = null;
              }}
              alt="Alexandria"
              className="block h-5 w-auto object-contain"
            />
            <Menu className="h-4 w-4 text-ink" />
          </div>

          {/* Search */}
          <div className="flex items-center gap-2 rounded-lg border border-mist bg-white px-3 py-2">
            <Search className="h-3.5 w-3.5 text-ink-secondary" />
            <span className="text-xs text-ink-secondary truncate">Search your memory…</span>
          </div>

          {/* Quick nav grid */}
          <div className="grid grid-cols-3 gap-2">
            {["Memory", "Context", "Sources"].map((n) => (
              <div key={n} className="rounded-md border border-mist bg-white py-2 text-center text-[10px] font-medium text-ink">
                {n}
              </div>
            ))}
          </div>

          {/* Compact metrics */}
          <div className="grid grid-cols-2 gap-2">
            <div className="rounded-md border border-mist bg-white p-2">
              <p className="text-[10px] text-ink-secondary">Packet</p>
              <p className="text-sm font-semibold text-ink">{data.metrics.admissiblePacket}</p>
            </div>
            <div className="rounded-md border border-mist bg-white p-2">
              <p className="text-[10px] text-ink-secondary">Confidence</p>
              <p className="text-sm font-semibold text-ink">{data.metrics.confidence}%</p>
            </div>
          </div>

          {/* Context preview */}
          <div className="rounded-md border border-mist bg-white p-2.5">
            <p className="text-[10px] font-semibold text-ink">Context Preview</p>
            <p className="text-[10px] text-ink-secondary mt-1">{data.contextPacket.objective}</p>
            <div className="mt-2 flex gap-2">
              <span className="text-[9px] bg-success-bg text-success px-1.5 py-0.5 rounded-full">{data.contextPacket.trustedSources} sources</span>
              <span className="text-[9px] bg-ivory-dark text-ink-secondary px-1.5 py-0.5 rounded-full">{data.contextPacket.policyConstraints} policies</span>
            </div>
          </div>

          {/* Route proof timeline */}
          <div className="rounded-md border border-mist bg-white p-2.5">
            <p className="text-[10px] font-semibold text-ink">Route Proof</p>
            <div className="mt-2 space-y-2">
              {data.routeProof.map((step) => (
                <div key={step.stage} className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-3 w-3 text-amber shrink-0" />
                  <span className="text-[10px] text-ink font-medium">{step.stage}</span>
                  <ArrowRight className="h-2.5 w-2.5 text-mist shrink-0" />
                  <span className="text-[10px] text-ink-secondary truncate">{step.label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Sources */}
          <div className="rounded-md border border-mist bg-white p-2.5">
            <p className="text-[10px] font-semibold text-ink">Sources</p>
            <div className="mt-2 space-y-1.5">
              {data.sources.slice(0, 3).map((s) => (
                <div key={s.name} className="flex items-center gap-1.5">
                  <FileText className="h-3 w-3 text-ink-secondary" />
                  <span className="text-[10px] text-ink truncate flex-1">{s.name}</span>
                  <span className="text-[9px] text-success">{s.status}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            <button
              onClick={() => void sendFeedback("useful")}
              className="flex-1 flex items-center justify-center gap-1 rounded-md bg-ink py-2 text-[10px] font-medium text-white hover:bg-graphite transition-colors"
            >
              <ThumbsUp className="h-3 w-3" /> Use
            </button>
            <button
              onClick={() => void sendFeedback("wrong")}
              className="flex-1 flex items-center justify-center gap-1 rounded-md border border-mist bg-white py-2 text-[10px] font-medium text-ink-secondary hover:bg-ivory transition-colors"
            >
              <ThumbsDown className="h-3 w-3" /> Reject
            </button>
            <button
              onClick={() => void sendFeedback("stale")}
              className="flex-1 flex items-center justify-center gap-1 rounded-md border border-mist bg-white py-2 text-[10px] font-medium text-warning hover:bg-warning-bg transition-colors"
            >
              <AlertTriangle className="h-3 w-3" /> Stale
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
