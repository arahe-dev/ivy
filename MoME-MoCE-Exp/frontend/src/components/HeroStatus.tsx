import { ShieldCheck, Database, AlertTriangle } from "lucide-react";
import type { AlexandriaDashboardData } from "../hooks/useAlexandriaHooks";

export default function HeroStatus({ data }: { data: AlexandriaDashboardData }) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl md:text-4xl font-bold text-ink leading-tight tracking-tight">
          Give any AI the right memory.
        </h1>
        <p className="mt-3 text-sm text-ink-secondary leading-relaxed">
          Alexandria recalls verified context, shows why it matters, and lets you decide what an agent can use.
        </p>
      </div>

      <div className="rounded-lg border border-mist bg-white p-4 space-y-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-success" />
          <span className="text-sm font-medium text-ink">Confidence {data.metrics.confidence}%</span>
          <span className="ml-auto text-xs font-medium text-success bg-success-bg px-2 py-0.5 rounded-full">
            {data.metrics.confidence >= 85 ? "High" : "Review"}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Database className="h-4 w-4 text-ink-secondary" />
          <span className="text-sm font-medium text-ink">Sources {data.contextPacket.trustedSources}</span>
          <span className="ml-auto text-xs font-medium text-success bg-success-bg px-2 py-0.5 rounded-full">Verified</span>
        </div>
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-ink-secondary" />
          <span className="text-sm font-medium text-ink">Stale warning {data.metrics.staleItems}</span>
          <span className="ml-auto text-xs font-medium text-success bg-success-bg px-2 py-0.5 rounded-full">
            {data.metrics.staleItems ? "Check" : "None"}
          </span>
        </div>
      </div>
    </div>
  );
}
