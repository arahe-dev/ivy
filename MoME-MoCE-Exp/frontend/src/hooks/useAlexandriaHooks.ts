import { useCallback, useEffect, useMemo, useState } from "react";
import {
  apiEndpoints as fallbackApiEndpoints,
  commandChips,
  contextBulletList,
  contextPacket,
  memoryFacts,
  memoryOverview,
  metrics,
  recallActivity,
  routeProof,
  sourceTableRows,
  sources,
  type ApiEndpoint,
  type MemoryFactRow,
  type RecallActivityItem,
  type RouteProofStep,
  type SourceItem,
  type SourceTableRow,
} from "../data/mockData";

export const DEFAULT_COMMAND = "Ship the v2 analytics dashboard for our AI agent product.";

export type ConnectionState = "loading" | "online" | "offline";

export interface DashboardMetrics {
  admissiblePacket: string;
  confidence: number;
  freshItems: number;
  staleItems: number;
  trustedSources: number;
  latencyMs?: number;
}

export interface MemoryOverview {
  preferences: number;
  aliases: number;
  projects: number;
  policies: number;
  notes: number;
  total: number;
}

export interface ContextPacketView {
  objective: string;
  relevantMemory: number;
  trustedSources: number;
  policyConstraints: number;
  bullets: string[];
  admittedLabel: string;
  excludedLabel: string;
  whyExcluded: string;
}

export interface ApiPreviewMetrics {
  response: string;
  time: string;
  confidence: string;
}

export interface AlexandriaDashboardData {
  apiBase: string;
  command: string;
  connection: ConnectionState;
  serviceLabel: string;
  error?: string;
  routeId?: string;
  metrics: DashboardMetrics;
  memoryOverview: MemoryOverview;
  contextPacket: ContextPacketView;
  routeProof: RouteProofStep[];
  sources: SourceItem[];
  sourceTableRows: SourceTableRow[];
  memoryFacts: MemoryFactRow[];
  recallActivity: RecallActivityItem[];
  apiEndpoints: ApiEndpoint[];
  apiRequest: string;
  apiPreview: ApiPreviewMetrics;
  commandChips: string[];
}

interface DogfoodHealth {
  ok: boolean;
  service_version: string;
  candidate_backend: string;
  memory_count: number;
  time: string;
}

interface DogfoodHooks {
  service_version: string;
  endpoints: ApiEndpoint[];
  packet_strategies: string[];
}

interface DogfoodMemory {
  id: string;
  source_family?: string;
  authority?: string;
  created_at?: string;
  claim_type?: string;
  staleness?: string;
  safety_label?: string;
  exposure_policy?: string;
  tags?: string[];
  aliases?: string[];
  provenance?: Record<string, unknown>;
  text_preview?: string;
  text?: string;
  score?: number;
}

interface DogfoodMemoryList {
  total: number;
  items: DogfoodMemory[];
}

interface DogfoodEvidence {
  id: string;
  source_family?: string;
  authority?: string;
  created_at?: string;
  staleness?: string;
  tags?: string[];
  provenance?: Record<string, unknown>;
  text?: string;
}

interface DogfoodContextBudget {
  max_evidence_items?: number;
  selected_evidence_items?: number;
  frontier_packet_tokens?: number;
  tokens_avoided?: number;
}

interface DogfoodPacket {
  query?: string;
  answerability?: string;
  evidence?: DogfoodEvidence[];
  constraints?: string[];
  context_budget?: DogfoodContextBudget;
}

interface DogfoodRouteProof {
  route_id?: string;
  decision?: string;
  strategy?: string;
  selected_ids?: string[];
  routes?: unknown[];
  intent_guard_rejections?: unknown[];
  latency_ms?: number;
}

interface DogfoodPacketResponse {
  route_id: string;
  strategy: string;
  decision: string;
  confidence: number;
  selected_ids: string[];
  latency_ms: number;
  packet: DogfoodPacket;
  route_summary?: {
    selected_ids?: string[];
    latency_ms?: number;
    decision?: string;
  };
  route_proof?: DogfoodRouteProof;
  _proof_path?: string;
}

interface DogfoodSnapshot {
  health: DogfoodHealth;
  hooks: DogfoodHooks;
  memories: DogfoodMemoryList;
}

const API_BASE = normalizeBaseUrl(import.meta.env.VITE_ALEXANDRIA_API_BASE || "http://127.0.0.1:8766");

export function useAlexandriaHooks() {
  const [query, setQuery] = useState(DEFAULT_COMMAND);
  const [connection, setConnection] = useState<ConnectionState>("loading");
  const [error, setError] = useState<string | undefined>();
  const [snapshot, setSnapshot] = useState<DogfoodSnapshot | null>(null);
  const [packet, setPacket] = useState<DogfoodPacketResponse | null>(null);
  const [proof, setProof] = useState<DogfoodRouteProof | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  const refresh = useCallback(async () => {
    setConnection((current) => (current === "online" ? "online" : "loading"));
    try {
      const nextSnapshot = await fetchSnapshot();
      setSnapshot(nextSnapshot);
      setConnection("online");
      setError(undefined);
      return nextSnapshot;
    } catch (err) {
      setConnection("offline");
      setError(errorMessage(err));
      return null;
    }
  }, []);

  const runPacket = useCallback(
    async (nextQuery?: string) => {
      const command = (nextQuery || query || DEFAULT_COMMAND).trim();
      if (!command) {
        return;
      }

      setQuery(command);
      setIsRunning(true);
      setError(undefined);

      try {
        const response = await postPacket(command);
        setPacket(response);
        setConnection("online");

        const proofPath = response._proof_path;
        if (response.route_proof) {
          setProof(response.route_proof);
        } else if (proofPath) {
          const stored = await fetchProof(proofPath);
          setProof(stored.route_proof || null);
        } else {
          setProof(null);
        }

        await refresh();
      } catch (err) {
        setConnection("offline");
        setError(errorMessage(err));
      } finally {
        setIsRunning(false);
      }
    },
    [query, refresh],
  );

  const sendFeedback = useCallback(
    async (rating: "useful" | "wrong" | "stale" | "missed" | "private" | "neutral", note?: string) => {
      if (!packet?.route_id) {
        return;
      }
      await requestJson("/feedback", {
        method: "POST",
        body: JSON.stringify({
          route_id: packet.route_id,
          rating,
          note: note || `Dashboard marked route ${rating}`,
        }),
      });
    },
    [packet?.route_id],
  );

  useEffect(() => {
    let active = true;

    async function loadInitial() {
      setConnection("loading");
      try {
        const nextSnapshot = await fetchSnapshot();
        if (!active) {
          return;
        }
        setSnapshot(nextSnapshot);
        setConnection("online");
        setError(undefined);

        const response = await postPacket(DEFAULT_COMMAND);
        if (!active) {
          return;
        }
        setPacket(response);
        if (response.route_proof) {
          setProof(response.route_proof);
        } else if (response._proof_path) {
          const stored = await fetchProof(response._proof_path);
          if (active) {
            setProof(stored.route_proof || null);
          }
        }
      } catch (err) {
        if (active) {
          setConnection("offline");
          setError(errorMessage(err));
        }
      }
    }

    void loadInitial();
    return () => {
      active = false;
    };
  }, []);

  const data = useMemo(
    () =>
      buildDashboardData({
        command: query,
        connection,
        error,
        snapshot,
        packet,
        proof,
      }),
    [connection, error, packet, proof, query, snapshot],
  );

  return {
    data,
    query,
    setQuery,
    runPacket,
    refresh,
    sendFeedback,
    isRunning,
  };
}

async function fetchSnapshot(): Promise<DogfoodSnapshot> {
  const [health, hooks, memories] = await Promise.all([
    requestJson<DogfoodHealth>("/health"),
    requestJson<DogfoodHooks>("/hooks"),
    requestJson<DogfoodMemoryList>("/memories?limit=50&offset=0&include_text=false"),
  ]);
  return { health, hooks, memories };
}

async function postPacket(query: string): Promise<DogfoodPacketResponse> {
  return requestJson<DogfoodPacketResponse>("/packet", {
    method: "POST",
    body: JSON.stringify({
      query,
      strategy: "helper-lazy",
      include_proof: false,
      max_evidence_items: 3,
    }),
  });
}

async function fetchProof(path: string): Promise<DogfoodPacketResponse> {
  return requestJson<DogfoodPacketResponse>(path.startsWith("/") ? path : `/${path}`);
}

async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

function buildDashboardData(args: {
  command: string;
  connection: ConnectionState;
  error?: string;
  snapshot: DogfoodSnapshot | null;
  packet: DogfoodPacketResponse | null;
  proof: DogfoodRouteProof | null;
}): AlexandriaDashboardData {
  const memories = args.snapshot?.memories.items || [];
  const evidence = args.packet?.packet.evidence || [];
  const hasLiveSnapshot = Boolean(args.snapshot);
  const hasLivePacket = Boolean(args.packet);
  const selectedIds = args.packet?.selected_ids || args.packet?.route_summary?.selected_ids || [];
  const packetSize = args.packet ? formatSize(args.packet.packet) : metrics.admissiblePacket;
  const confidence = args.packet ? normalizeConfidence(args.packet.confidence) : metrics.confidence;
  const staleItems = hasLiveSnapshot
    ? memories.filter((item) => item.staleness && item.staleness !== "current").length
    : metrics.staleItems;
  const freshItems = hasLiveSnapshot
    ? memories.filter((item) => !item.staleness || item.staleness === "current").length
    : metrics.freshItems;
  const trustedSources = hasLiveSnapshot ? countTrustedSources(evidence, memories) : metrics.trustedSources;
  const admittedCount = evidence.length || selectedIds.length;
  const maxEvidence = args.packet?.packet.context_budget?.max_evidence_items ?? (hasLivePacket ? admittedCount : contextPacket.relevantMemory);

  return {
    apiBase: API_BASE,
    command: args.command,
    connection: args.connection,
    serviceLabel: serviceLabel(args.connection, args.snapshot),
    error: args.error,
    routeId: args.packet?.route_id,
    metrics: {
      admissiblePacket: packetSize,
      confidence,
      freshItems,
      staleItems,
      trustedSources,
      latencyMs: args.packet?.latency_ms,
    },
    memoryOverview: hasLiveSnapshot ? buildMemoryOverview(memories) : memoryOverview,
    contextPacket: {
      objective: args.packet?.packet.query || args.command || contextPacket.objective,
      relevantMemory: hasLivePacket ? admittedCount : contextPacket.relevantMemory,
      trustedSources,
      policyConstraints: args.packet?.packet.constraints?.length || contextPacket.policyConstraints,
      bullets: buildContextBullets(evidence, hasLivePacket),
      admittedLabel: `${admittedCount}/${maxEvidence}`,
      excludedLabel: `${Math.max(0, maxEvidence - admittedCount)} items`,
      whyExcluded: args.packet ? "stale, low relevance, policy blocked, or outside the current task" : "stale, low relevance, policy blocked",
    },
    routeProof: buildRouteProof(args.snapshot, args.packet, args.proof, packetSize),
    sources: buildSources(evidence, memories, hasLiveSnapshot),
    sourceTableRows: buildSourceTableRows(evidence, memories, hasLiveSnapshot),
    memoryFacts: buildMemoryFacts(memories, hasLiveSnapshot),
    recallActivity: buildRecallActivity(args.packet, args.command),
    apiEndpoints: args.snapshot?.hooks.endpoints?.length ? args.snapshot.hooks.endpoints : fallbackApiEndpoints,
    apiRequest: JSON.stringify(
      {
        query: args.command,
        strategy: "helper-lazy",
        include_proof: false,
        max_evidence_items: 3,
      },
      null,
      2,
    ),
    apiPreview: {
      response: packetSize,
      time: args.packet?.latency_ms ? `${args.packet.latency_ms.toFixed(2)} ms` : "offline",
      confidence: `${confidence}%`,
    },
    commandChips,
  };
}

function buildMemoryOverview(memories: DogfoodMemory[]): MemoryOverview {
  const aliases = memories.reduce((sum, item) => sum + (item.aliases?.length || 0), 0);
  const policies = memories.filter((item) => {
    const tags = item.tags || [];
    return item.claim_type === "policy" || item.safety_label !== "normal" || tags.some((tag) => tag.includes("policy") || tag.includes("security"));
  }).length;
  const projects = new Set(memories.flatMap((item) => (item.tags || []).filter((tag) => tag.includes("project") || tag.includes("repo")))).size;
  const preferences = memories.filter((item) => item.claim_type === "preference" || (item.tags || []).includes("preference")).length;

  return {
    preferences,
    aliases,
    projects,
    policies,
    notes: Math.max(0, memories.length - preferences - policies),
    total: memories.length,
  };
}

function buildContextBullets(evidence: DogfoodEvidence[], hasLivePacket: boolean): string[] {
  if (!evidence.length) {
    if (hasLivePacket) {
      return ["No admitted memory for this command yet. The model should answer without project memory."];
    }
    return contextBulletList;
  }
  return evidence.slice(0, 6).map((item) => `${displaySourceName(item)}: ${truncate(item.text || item.id, 130)}`);
}

function buildRouteProof(
  snapshot: DogfoodSnapshot | null,
  packet: DogfoodPacketResponse | null,
  proof: DogfoodRouteProof | null,
  packetSize: string,
): RouteProofStep[] {
  if (!packet) {
    return routeProof;
  }

  const selected = packet.selected_ids?.length || packet.packet.context_budget?.selected_evidence_items || 0;
  const routeCount = Array.isArray(proof?.routes) ? proof.routes.length : 1;
  const rejected = Array.isArray(proof?.intent_guard_rejections) ? proof.intent_guard_rejections.length : 0;

  return [
    { stage: "Ingest", label: `${snapshot?.health.memory_count ?? 0} memories loaded`, detail: snapshot?.health.candidate_backend || "" },
    { stage: "Route", label: `${packet.strategy} · ${routeCount} route${routeCount === 1 ? "" : "s"}`, detail: packet.decision },
    { stage: "Evaluate", label: `${selected} admitted${rejected ? ` · ${rejected} guard rejects` : ""}`, detail: "D-ACCA admission gate applied" },
    { stage: "Assemble", label: `Packet built (${packetSize})`, detail: `${packet.packet.context_budget?.frontier_packet_tokens ?? 0} est. tokens` },
    { stage: "Output", label: "Proof stored", detail: packet.route_id },
  ];
}

function buildSources(evidence: DogfoodEvidence[], memories: DogfoodMemory[], hasLiveSnapshot: boolean): SourceItem[] {
  const items = evidence.length ? evidence : memories.slice(0, 5);
  if (!items.length) {
    if (hasLiveSnapshot) {
      return [{ name: "No admitted evidence yet", type: "Packet", status: "Waiting", time: "live" }];
    }
    return sources;
  }
  return items.slice(0, 5).map((item) => ({
    name: displaySourceName(item),
    type: titleCase(item.source_family || "memory"),
    status: statusLabel(item),
    time: item.created_at || "stored",
  }));
}

function buildSourceTableRows(evidence: DogfoodEvidence[], memories: DogfoodMemory[], hasLiveSnapshot: boolean): SourceTableRow[] {
  const items = evidence.length ? evidence : memories.slice(0, 8);
  if (!items.length) {
    if (hasLiveSnapshot) {
      return [
        {
          name: "No ingested source records",
          type: "Memory",
          status: "Waiting",
          lastSeen: "live",
          routeNote: "Use /ingest to add project memory",
        },
      ];
    }
    return sourceTableRows;
  }
  return items.slice(0, 8).map((item) => ({
    name: displaySourceName(item),
    type: titleCase(item.source_family || "memory"),
    status: statusLabel(item),
    lastSeen: item.created_at || "stored",
    routeNote: item.staleness === "current" || !item.staleness ? "Admissible candidate" : `${titleCase(item.staleness)} evidence`,
  }));
}

function buildMemoryFacts(memories: DogfoodMemory[], hasLiveSnapshot: boolean): MemoryFactRow[] {
  if (!memories.length) {
    if (hasLiveSnapshot) {
      return [
        {
          fact: "No ingested memories yet",
          type: "Memory",
          cluster: "dogfood",
          freshness: "Stale",
          lastSeen: "waiting",
        },
      ];
    }
    return memoryFacts;
  }
  return memories.slice(0, 8).map((item) => ({
    fact: truncate(item.text_preview || item.text || item.id, 88),
    type: titleCase(item.claim_type || item.source_family || "fact"),
    cluster: item.tags?.[0] || item.source_family || "memory",
    freshness: item.staleness && item.staleness !== "current" ? "Stale" : "Fresh",
    lastSeen: item.created_at || "stored",
  }));
}

function buildRecallActivity(packet: DogfoodPacketResponse | null, command: string): RecallActivityItem[] {
  if (!packet) {
    return recallActivity;
  }
  return [
    {
      action: "Packet built",
      detail: `${truncate(command, 52)} · ${packet.selected_ids.length} admitted`,
      time: "just now",
    },
    ...recallActivity,
  ].slice(0, 5);
}

function countTrustedSources(evidence: DogfoodEvidence[], memories: DogfoodMemory[]) {
  const items = evidence.length ? evidence : memories;
  return items.filter((item) => item.authority === "high" || item.authority === "medium" || !item.authority).length;
}

function displaySourceName(item: Pick<DogfoodMemory, "id" | "provenance" | "source_family">) {
  const artifactPath = asString(item.provenance?.artifact_path);
  if (artifactPath) {
    return artifactPath.split(/[\\/]/).filter(Boolean).at(-1) || item.id;
  }
  return item.id || item.source_family || "memory";
}

function statusLabel(item: Pick<DogfoodMemory, "authority" | "staleness" | "safety_label">) {
  if (item.staleness && item.staleness !== "current") {
    return titleCase(item.staleness);
  }
  if (item.safety_label && item.safety_label !== "normal") {
    return titleCase(item.safety_label);
  }
  return item.authority === "high" || item.authority === "medium" || !item.authority ? "Verified" : titleCase(item.authority);
}

function serviceLabel(connection: ConnectionState, snapshot: DogfoodSnapshot | null) {
  if (connection === "online" && snapshot) {
    return `Live · ${snapshot.health.memory_count.toLocaleString()} memories · ${snapshot.health.candidate_backend}`;
  }
  if (connection === "loading") {
    return "Connecting to D-ACCA";
  }
  return "Mock fallback · start D-ACCA hooks on :8766";
}

function normalizeConfidence(value: number) {
  const percent = value <= 1 ? value * 100 : value;
  return Math.max(0, Math.min(100, Math.round(percent)));
}

function normalizeBaseUrl(value: string) {
  return value.replace(/\/+$/, "");
}

function formatSize(value: unknown) {
  const bytes = JSON.stringify(value ?? {}).length;
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  return `${(bytes / 1024).toFixed(1)} KB`;
}

function titleCase(value?: string) {
  return (value || "unknown")
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function truncate(value: string, maxLength: number) {
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}…` : value;
}

function asString(value: unknown) {
  return typeof value === "string" ? value : "";
}

function errorMessage(err: unknown) {
  return err instanceof Error ? err.message : String(err);
}
