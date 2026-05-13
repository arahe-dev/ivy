import { Check } from "lucide-react";

export default function AccessSection() {
  return (
    <section>
      <h2 className="text-xl font-semibold text-ink">Access</h2>

      <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Private Beta */}
        <div className="rounded-lg border-2 border-amber bg-white p-5 relative">
          <div className="absolute -top-3 left-4 bg-amber text-white text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full">
            Recommended
          </div>
          <h3 className="text-base font-semibold text-ink">Private Beta</h3>
          <ul className="mt-3 space-y-2">
            {[
              "Local-first & private",
              "256-bit encryption at rest",
              "Bring your own infra",
              "Audit logs & access controls",
            ].map((item) => (
              <li key={item} className="flex items-center gap-2 text-sm text-ink-secondary">
                <Check className="h-4 w-4 text-success shrink-0" />
                {item}
              </li>
            ))}
          </ul>
          <button className="mt-5 inline-flex items-center rounded-md bg-ink px-4 py-2 text-sm font-medium text-white hover:bg-graphite transition-colors">
            Request Access
          </button>
        </div>

        {/* Enterprise */}
        <div className="rounded-lg border border-mist bg-white p-5">
          <h3 className="text-base font-semibold text-ink">Enterprise — Coming soon</h3>
          <ul className="mt-3 space-y-2">
            {[
              "SLA & priority support",
              "SSO & SCIM",
              "Custom retention policies",
              "On-prem / VPC deployment",
            ].map((item) => (
              <li key={item} className="flex items-center gap-2 text-sm text-ink-secondary">
                <Check className="h-4 w-4 text-mist shrink-0" />
                {item}
              </li>
            ))}
          </ul>
          <button className="mt-5 inline-flex items-center rounded-md border border-mist bg-white px-4 py-2 text-sm font-medium text-ink-secondary hover:bg-ivory transition-colors">
            Contact Sales
          </button>
        </div>
      </div>
    </section>
  );
}
