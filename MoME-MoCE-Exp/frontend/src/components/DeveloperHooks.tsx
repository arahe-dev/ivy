import type { ApiEndpoint } from "../data/mockData";
import type { ApiPreviewMetrics, ConnectionState } from "../hooks/useAlexandriaHooks";

export default function DeveloperHooks({
  apiBase,
  endpoints,
  request,
  preview,
  connection,
}: {
  apiBase: string;
  endpoints: ApiEndpoint[];
  request: string;
  preview: ApiPreviewMetrics;
  connection: ConnectionState;
}) {
  return (
    <section>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-ink">Developer hooks — API preview</h2>
          <p className="mt-1 text-xs font-mono text-ink-secondary">{apiBase}</p>
        </div>
        <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${
          connection === "online" ? "bg-success-bg text-success" : "bg-warning-bg text-warning"
        }`}>
          {connection === "online" ? "Live hooks" : "Mock fallback"}
        </span>
      </div>

      <div className="mt-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="rounded-lg border border-mist bg-white p-4">
          <h3 className="text-sm font-semibold text-ink">Endpoints</h3>
          <div className="mt-3 space-y-2">
            {endpoints.map((ep) => (
              <div key={ep.path} className="flex items-center gap-2 rounded-md bg-ivory px-3 py-2">
                <span className="text-[10px] font-bold uppercase tracking-wide text-amber">{ep.method}</span>
                <span className="text-sm font-mono text-ink">{ep.path}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="lg:col-span-2 rounded-lg border border-mist bg-white p-4">
          <h3 className="text-sm font-semibold text-ink">Sample Request</h3>
          <pre className="mt-3">{request}</pre>

          <div className="mt-4 grid grid-cols-3 gap-3">
            <div className="rounded-md border border-mist bg-ivory p-3">
              <p className="text-[10px] font-semibold text-ink-secondary uppercase tracking-wide">Response</p>
              <p className="mt-1 text-sm font-semibold text-ink">{preview.response}</p>
            </div>
            <div className="rounded-md border border-mist bg-ivory p-3">
              <p className="text-[10px] font-semibold text-ink-secondary uppercase tracking-wide">Time</p>
              <p className="mt-1 text-sm font-semibold text-ink">{preview.time}</p>
            </div>
            <div className="rounded-md border border-mist bg-ivory p-3">
              <p className="text-[10px] font-semibold text-ink-secondary uppercase tracking-wide">Confidence</p>
              <p className="mt-1 text-sm font-semibold text-ink">{preview.confidence}</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
