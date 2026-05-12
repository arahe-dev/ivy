import { useState } from "react";
import { ShieldCheck, Clock, AlertTriangle } from "lucide-react";
import type { MemoryFactRow } from "../data/mockData";

const tabs = ["Stored facts", "Aliases", "Clusters", "Freshness", "Stale warning"];

export default function MemorySection({ rows }: { rows: MemoryFactRow[] }) {
  const [activeTab, setActiveTab] = useState("Stored facts");

  return (
    <section id="memory" className="scroll-mt-28">
      <h2 className="text-xl font-semibold text-ink">Memory — What Alexandria remembers</h2>

      <div className="mt-4 inline-flex rounded-lg border border-mist bg-white p-1">
        {tabs.map((t) => (
          <button
            key={t}
            onClick={() => setActiveTab(t)}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              activeTab === t ? "bg-ink text-white" : "text-ink-secondary hover:bg-ivory"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="mt-4 rounded-lg border border-mist bg-white overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-mist bg-ivory">
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-ink-secondary uppercase tracking-wide">Fact</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-ink-secondary uppercase tracking-wide">Type</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-ink-secondary uppercase tracking-wide">Cluster</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-ink-secondary uppercase tracking-wide">Freshness</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-ink-secondary uppercase tracking-wide">Last seen</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.fact} className="border-b border-mist-light last:border-b-0 hover:bg-ivory/50 transition-colors">
                  <td className="px-4 py-3 text-ink font-medium whitespace-nowrap">{row.fact}</td>
                  <td className="px-4 py-3 text-ink-secondary">{row.type}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center rounded-md bg-ivory-dark px-2 py-0.5 text-xs font-medium text-ink-secondary">
                      {row.cluster}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
                      row.freshness === "Fresh"
                        ? "bg-success-bg text-success"
                        : "bg-warning-bg text-warning"
                    }`}>
                      {row.freshness === "Fresh" ? <ShieldCheck className="h-3 w-3" /> : <AlertTriangle className="h-3 w-3" />}
                      {row.freshness}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-ink-secondary flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {row.lastSeen}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
