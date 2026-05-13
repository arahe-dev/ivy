import { MessageSquare, Database, Package, ShieldCheck } from "lucide-react";

const steps = [
  {
    icon: <MessageSquare className="h-5 w-5" />,
    title: "Ask",
    desc: "You ask a question or give an agent task",
  },
  {
    icon: <Database className="h-5 w-5" />,
    title: "Recall",
    desc: "Alexandria recalls relevant memory from your vault",
  },
  {
    icon: <Package className="h-5 w-5" />,
    title: "Packet",
    desc: "We build an admissible context packet",
  },
  {
    icon: <ShieldCheck className="h-5 w-5" />,
    title: "Proof",
    desc: "We show why it was included and from where",
  },
];

export default function HowItWorks() {
  return (
    <section>
      <h2 className="text-xl font-semibold text-ink">How it works</h2>
      <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {steps.map((step, i) => (
          <div key={step.title} className="rounded-lg border border-mist bg-white p-4 relative">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-full bg-ivory flex items-center justify-center text-ink">
                {step.icon}
              </div>
              <span className="text-xs font-semibold text-ink-secondary">0{i + 1}</span>
            </div>
            <h3 className="mt-3 text-sm font-semibold text-ink">{step.title}</h3>
            <p className="mt-1 text-xs text-ink-secondary leading-relaxed">{step.desc}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
