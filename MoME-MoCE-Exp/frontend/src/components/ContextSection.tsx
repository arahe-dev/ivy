import { CheckCircle2, XCircle, ShieldCheck, Package } from "lucide-react";
import type { ContextPacketView, DashboardMetrics } from "../hooks/useAlexandriaHooks";

export default function ContextSection({ data, metrics }: { data: ContextPacketView; metrics: DashboardMetrics }) {
  return (
    <section id="context" className="scroll-mt-28">
      <h2 className="text-xl font-semibold text-ink">Context — What gets injected</h2>

      <div className="mt-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 rounded-lg border border-mist bg-white p-4">
          <h3 className="text-sm font-semibold text-ink">Admissible Context Packet</h3>
          <ul className="mt-3 space-y-2">
            {data.bullets.map((item) => (
              <li key={item} className="flex items-start gap-2 text-sm text-ink">
                <CheckCircle2 className="h-4 w-4 text-success shrink-0 mt-0.5" />
                {item}
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-lg border border-mist bg-white p-4 space-y-3">
          <h3 className="text-sm font-semibold text-ink">Packet Summary</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-ink-secondary flex items-center gap-1"><Package className="h-3.5 w-3.5" /> Size</span>
              <span className="font-medium text-ink">{metrics.admissiblePacket}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-ink-secondary flex items-center gap-1"><ShieldCheck className="h-3.5 w-3.5" /> Confidence</span>
              <span className="font-medium text-ink">{metrics.confidence}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-ink-secondary flex items-center gap-1"><CheckCircle2 className="h-3.5 w-3.5" /> Admitted</span>
              <span className="font-medium text-success">{data.admittedLabel}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-ink-secondary flex items-center gap-1"><XCircle className="h-3.5 w-3.5" /> Excluded</span>
              <span className="font-medium text-ink-secondary">{data.excludedLabel}</span>
            </div>
          </div>
          <div className="rounded-md bg-ivory p-3">
            <p className="text-xs font-semibold text-ink-secondary uppercase tracking-wide mb-1">Why excluded</p>
            <p className="text-xs text-ink-secondary">{data.whyExcluded}</p>
          </div>
        </div>
      </div>
    </section>
  );
}
