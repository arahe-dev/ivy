import { useState } from "react";
import { CheckCircle2, AlertTriangle, Trash2 } from "lucide-react";
import { recallTabs, recallRows } from "../data/mockData";

const statusConfig: Record<string, { icon: React.ReactNode; color: string; bg: string }> = {
  confirmed: { icon: <CheckCircle2 className="h-3.5 w-3.5" />, color: "text-success", bg: "bg-success-bg" },
  corrected: { icon: <AlertTriangle className="h-3.5 w-3.5" />, color: "text-warning", bg: "bg-warning-bg" },
  forgotten: { icon: <Trash2 className="h-3.5 w-3.5" />, color: "text-ink-secondary", bg: "bg-ivory-dark" },
};

export default function RecallSection() {
  const [activeTab, setActiveTab] = useState("Activity");

  return (
    <section id="recall" className="scroll-mt-28">
      <h2 className="text-xl font-semibold text-ink">Recall — Feedback loop</h2>

      <div className="mt-4 inline-flex rounded-lg border border-mist bg-white p-1">
        {recallTabs.map((t) => (
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
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-ink-secondary uppercase tracking-wide">Status</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-ink-secondary uppercase tracking-wide">Description</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-ink-secondary uppercase tracking-wide">Time</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-ink-secondary uppercase tracking-wide">Action</th>
              </tr>
            </thead>
            <tbody>
              {recallRows.map((row) => {
                const cfg = statusConfig[row.status] || statusConfig.confirmed;
                return (
                  <tr key={row.description} className="border-b border-mist-light last:border-b-0 hover:bg-ivory/50 transition-colors">
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${cfg.bg} ${cfg.color}`}>
                        {cfg.icon}
                        {row.status.charAt(0).toUpperCase() + row.status.slice(1)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-ink whitespace-nowrap">{row.description}</td>
                    <td className="px-4 py-3 text-ink-secondary whitespace-nowrap">{row.time}</td>
                    <td className="px-4 py-3">
                      <button className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                        row.action === "Forgotten"
                          ? "bg-ivory-dark text-ink-secondary"
                          : "bg-ink text-white hover:bg-graphite"
                      }`}>
                        {row.action}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
