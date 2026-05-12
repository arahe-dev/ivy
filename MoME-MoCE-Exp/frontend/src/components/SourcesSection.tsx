import { useState } from "react";
import { FileText, ShieldCheck } from "lucide-react";
import { sourceTabs, type SourceTableRow } from "../data/mockData";

export default function SourcesSection({ rows }: { rows: SourceTableRow[] }) {
  const [activeTab, setActiveTab] = useState("Files");

  return (
    <section id="sources" className="scroll-mt-28">
      <h2 className="text-xl font-semibold text-ink">Sources — Provenance & trusted inputs</h2>

      <div className="mt-4 inline-flex rounded-lg border border-mist bg-white p-1">
        {sourceTabs.map((t) => (
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
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-ink-secondary uppercase tracking-wide">Source</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-ink-secondary uppercase tracking-wide">Type</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-ink-secondary uppercase tracking-wide">Status</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-ink-secondary uppercase tracking-wide">Last seen</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-ink-secondary uppercase tracking-wide">Route notes</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.name} className="border-b border-mist-light last:border-b-0 hover:bg-ivory/50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-ink-secondary shrink-0" />
                      <span className="font-medium text-ink whitespace-nowrap">{row.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-ink-secondary">{row.type}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center gap-1 rounded-full bg-success-bg px-2 py-0.5 text-xs font-medium text-success">
                      <ShieldCheck className="h-3 w-3" />
                      {row.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-ink-secondary whitespace-nowrap">{row.lastSeen}</td>
                  <td className="px-4 py-3 text-ink-secondary">{row.routeNote}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
