export interface RouteProofStep {
  stage: string;
  label: string;
  detail: string;
}

export interface SourceItem {
  name: string;
  type: string;
  status: string;
  time: string;
}

export interface MemoryFactRow {
  fact: string;
  type: string;
  cluster: string;
  freshness: "Fresh" | "Stale";
  lastSeen: string;
}

export interface SourceTableRow {
  name: string;
  type: string;
  status: string;
  lastSeen: string;
  routeNote: string;
}

export interface RecallActivityItem {
  action: string;
  detail: string;
  time: string;
}

export interface RecallRow {
  status: string;
  description: string;
  time: string;
  action: string;
}

export interface ApiEndpoint {
  method: string;
  path: string;
  read_only?: boolean;
}

export const commandChips = [
  "How should Alexandria connect to D-ACCA hooks?",
  "How do I ingest memory into Alexandria?",
  "Why was this evidence included?",
];

export const metrics = {
  admissiblePacket: "18.7 KB",
  confidence: 92,
  freshItems: 2136,
  staleItems: 23,
  trustedSources: 128,
};

export const memoryOverview = {
  preferences: 142,
  aliases: 18,
  projects: 9,
  policies: 12,
  notes: 2661,
  total: 2842,
};

export const contextPacket = {
  objective: "Ship the v2 analytics dashboard",
  relevantMemory: 9,
  trustedSources: 6,
  policyConstraints: 4,
};

export const routeProof: RouteProofStep[] = [
  { stage: "Ingest", label: "38 items received", detail: "" },
  { stage: "Route", label: "35 → 14 candidates", detail: "Filtered by relevance & policy" },
  { stage: "Evaluate", label: "14 → 9 admissible", detail: "Scored and ranked" },
  { stage: "Assemble", label: "Packet built (18.7 KB)", detail: "Within budget" },
  { stage: "Output", label: "Proof generated", detail: "Verifiable trace ready" },
];

export const sources: SourceItem[] = [
  { name: "productPRD.md", type: "Docs", status: "Verified", time: "2m ago" },
  { name: "design-system.md", type: "Docs", status: "Verified", time: "6m ago" },
  { name: "sprint-plan.md", type: "Docs", status: "Verified", time: "18m ago" },
  { name: "#eng-standup", type: "Slack", status: "Verified", time: "1h ago" },
  { name: "analytics.py", type: "GitHub", status: "Verified", time: "2h ago" },
];

export const recallActivity: RecallActivityItem[] = [
  { action: "Remembered preference", detail: "PowerShell over bash", time: "2m ago" },
  { action: "Correction accepted", detail: "Use Node 20 LTS", time: "15m ago" },
  { action: "Fact confirmed", detail: "Project repo is alexandria/engine", time: "1h ago" },
  { action: "Forget request", detail: "Old deployment token", time: "3h ago" },
];

export const memoryFacts: MemoryFactRow[] = [
  { fact: "Prefers PowerShell over bash", type: "Preference", cluster: "DevEnv", freshness: "Fresh", lastSeen: "2m ago" },
  { fact: "Uses Node.js 20 LTS", type: "Preference", cluster: "DevEnv", freshness: "Fresh", lastSeen: "15m ago" },
  { fact: "Main repo: alexandria/engine", type: "Fact", cluster: "Project", freshness: "Fresh", lastSeen: "1h ago" },
  { fact: "Deployed on AWS us-east-1", type: "Fact", cluster: "Infra", freshness: "Fresh", lastSeen: "3h ago" },
  { fact: "Never share API keys", type: "Policy", cluster: "Security", freshness: "Fresh", lastSeen: "1d ago" },
];

export const contextBulletList = [
  "Stack: Next.js 14, App Router, TypeScript, Tailwind, Vercel",
  "Data: Postgres (Neon) with Drizzle ORM",
  "UI: shadcn/ui + Radix primitives",
  "Testing: Playwright for E2E",
  "Repo: github.com/your-org/agent-dashboard",
];

export const sourceTabs = ["Files", "Logs", "Docs", "Conversations", "Repo"];
export const sourceTableRows: SourceTableRow[] = [
  { name: "productPRD.md", type: "Docs", status: "Verified", lastSeen: "2m ago", routeNote: "High relevance" },
  { name: "design-system.md", type: "Docs", status: "Verified", lastSeen: "6m ago", routeNote: "Style context" },
  { name: "sprint-plan.md", type: "Docs", status: "Verified", lastSeen: "18m ago", routeNote: "Timeline anchor" },
  { name: "#eng-standup", type: "Slack", status: "Verified", lastSeen: "1h ago", routeNote: "Recent decisions" },
  { name: "analytics.py", type: "GitHub", status: "Verified", lastSeen: "2h ago", routeNote: "Data layer ref" },
];

export const recallTabs = ["Activity", "Corrections", "Confirmations", "Forgets"];
export const recallRows: RecallRow[] = [
  { status: "confirmed", description: "Remembered preference: PowerShell over bash", time: "2m ago", action: "Keep" },
  { status: "corrected", description: "Correction accepted: Use Node 20 LTS", time: "15m ago", action: "Keep" },
  { status: "confirmed", description: "Fact confirmed: Project repo is alexandria/engine", time: "1h ago", action: "Keep" },
  { status: "forgotten", description: "Forget request: Old deployment token", time: "3h ago", action: "Forgotten" },
];

export const apiEndpoints: ApiEndpoint[] = [
  { method: "POST", path: "/ingest" },
  { method: "POST", path: "/packet" },
  { method: "GET", path: "/proof" },
  { method: "POST", path: "/feedback" },
  { method: "POST", path: "/forget" },
];

export const apiRequest = `{
  "objective": "Ship the v2 analytics dashboard",
  "agent": "claude-3.5-sonnet",
  "max_kb": 20,
  "include_sources": true,
  "policies": ["no_secrets", "verify_before_advising"]
}`;
