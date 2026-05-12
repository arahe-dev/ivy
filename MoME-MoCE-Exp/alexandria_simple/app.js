const DEFAULT_API_BASE = "http://127.0.0.1:8766";

const state = {
  apiBase: DEFAULT_API_BASE,
  health: null,
  hooks: null,
  memories: [],
  packetResponse: null,
  proofResponse: null,
  searchResults: [],
  busy: false,
};

const els = {};

document.addEventListener("DOMContentLoaded", () => {
  bindElements();
  bindActions();
  const url = new URL(window.location.href);
  state.apiBase = url.searchParams.get("api") || localStorage.getItem("alexandria_simple_api") || DEFAULT_API_BASE;
  els.apiBase.value = state.apiBase;
  refreshAll();
});

function bindElements() {
  for (const id of [
    "apiBase",
    "saveApiBtn",
    "refreshBtn",
    "seedBtn",
    "queryInput",
    "packetHelperBtn",
    "packetDirectBtn",
    "copyPacketBtn",
    "memoryText",
    "memoryId",
    "memoryTags",
    "sourceFamily",
    "authority",
    "ingestBtn",
    "searchInput",
    "searchBtn",
    "forgetInput",
    "forgetBtn",
    "statusDot",
    "statusText",
    "memoryCount",
    "selectedCount",
    "confidence",
    "latency",
    "routeSummary",
    "routeId",
    "evidenceList",
    "memoryList",
    "packetJson",
    "proofJson",
    "searchResults",
    "log",
  ]) {
    els[id] = document.getElementById(id);
  }
}

function bindActions() {
  els.saveApiBtn.addEventListener("click", saveApiBase);
  els.refreshBtn.addEventListener("click", refreshAll);
  els.seedBtn.addEventListener("click", seedDogfoodMemory);
  els.packetHelperBtn.addEventListener("click", () => buildPacket("helper-lazy"));
  els.packetDirectBtn.addEventListener("click", () => buildPacket("d-acca"));
  els.copyPacketBtn.addEventListener("click", copyModelPacket);
  els.ingestBtn.addEventListener("click", ingestMemory);
  els.searchBtn.addEventListener("click", searchMemory);
  els.forgetBtn.addEventListener("click", forgetMemories);
  document.querySelectorAll("[data-rating]").forEach((button) => {
    button.addEventListener("click", () => sendFeedback(button.dataset.rating));
  });
}

function saveApiBase() {
  state.apiBase = normalizeBase(els.apiBase.value || DEFAULT_API_BASE);
  els.apiBase.value = state.apiBase;
  localStorage.setItem("alexandria_simple_api", state.apiBase);
  log(`Saved API base ${state.apiBase}`);
  refreshAll();
}

async function refreshAll() {
  return runBusy(async () => {
    state.apiBase = normalizeBase(els.apiBase.value || state.apiBase || DEFAULT_API_BASE);
    const [health, hooks, memories] = await Promise.all([
      requestJson("/health"),
      requestJson("/hooks"),
      requestJson("/memories?limit=100&offset=0&include_text=false"),
    ]);
    state.health = health;
    state.hooks = hooks;
    state.memories = Array.isArray(memories.items) ? memories.items : [];
    setOnline(true, `Live - ${health.memory_count} memories - ${health.candidate_backend}`);
    log(`Connected to ${health.service_version}; ${health.memory_count} memories.`);
    render();
  }, "refresh failed");
}

async function seedDogfoodMemory() {
  return runBusy(async () => {
    const result = await requestJson("/ingest", {
      method: "POST",
      body: JSON.stringify({
        source: "alexandria_simple_seed",
        project: "alexandria",
        items: ALEXANDRIA_SEED_ITEMS,
      }),
    });
    log(`Seeded ${result.ingested} memories; corpus now has ${result.memory_count}.`);
    await refreshAll();
    await buildPacket("helper-lazy");
  }, "seed failed");
}

async function buildPacket(strategy) {
  return runBusy(async () => {
    const query = els.queryInput.value.trim();
    if (!query) {
      throw new Error("Query is empty.");
    }
    const packet = await requestJson("/packet", {
      method: "POST",
      body: JSON.stringify({
        query,
        strategy,
        include_proof: false,
        max_evidence_items: 4,
      }),
    });
    state.packetResponse = packet;
    const proofPath = packet._proof_path || (packet.route_id ? `/proof/${packet.route_id}` : "");
    state.proofResponse = proofPath ? await requestJson(proofPath) : null;
    log(`Built ${strategy} packet ${packet.route_id} with ${packet.selected_ids.length} admitted item(s).`);
    await refreshAll();
    render();
  }, "packet failed");
}

async function ingestMemory() {
  return runBusy(async () => {
    const text = els.memoryText.value.trim();
    if (!text) {
      throw new Error("Memory text is empty.");
    }
    const tags = splitCsv(els.memoryTags.value);
    const payload = {
      items: [
        {
          id: els.memoryId.value.trim() || undefined,
          text,
          source_family: els.sourceFamily.value,
          authority: els.authority.value,
          claim_type: "fact",
          tags,
          aliases: tags,
          helper_query: `${tags.join(" ")} ${text.slice(0, 180)}`.trim(),
          guard_terms: tags.slice(0, 4),
          replay_match_terms: tags,
        },
      ],
    };
    const result = await requestJson("/ingest", { method: "POST", body: JSON.stringify(payload) });
    els.memoryText.value = "";
    els.memoryId.value = "";
    log(`Ingested ${result.ingested} memory: ${result.ids.join(", ")}`);
    await refreshAll();
  }, "ingest failed");
}

async function searchMemory() {
  return runBusy(async () => {
    const query = els.searchInput.value.trim();
    if (!query) {
      throw new Error("Search query is empty.");
    }
    const result = await requestJson(`/search?q=${encodeURIComponent(query)}&limit=12&include_text=false`);
    state.searchResults = Array.isArray(result.items) ? result.items : [];
    log(`Search "${query}" returned ${state.searchResults.length} item(s).`);
    renderSearchResults();
  }, "search failed");
}

async function sendFeedback(rating) {
  return runBusy(async () => {
    if (!state.packetResponse || !state.packetResponse.route_id) {
      throw new Error("No route_id yet. Build a packet first.");
    }
    const result = await requestJson("/feedback", {
      method: "POST",
      body: JSON.stringify({
        route_id: state.packetResponse.route_id,
        rating,
        note: `Simple UI marked route ${rating}`,
      }),
    });
    log(`Feedback saved: ${result.feedback.rating} for ${result.feedback.route_id}`);
  }, "feedback failed");
}

async function forgetMemories() {
  return runBusy(async () => {
    const ids = splitCsv(els.forgetInput.value);
    if (!ids.length) {
      throw new Error("No memory IDs supplied.");
    }
    const result = await requestJson("/forget", {
      method: "POST",
      body: JSON.stringify({ ids, reason: "forgot from Alexandria simple UI" }),
    });
    els.forgetInput.value = "";
    log(`Forgot ${result.removed} record(s): ${result.ids.join(", ")}`);
    await refreshAll();
  }, "forget failed");
}

async function copyModelPacket() {
  if (!state.packetResponse || !state.packetResponse.packet) {
    log("No model packet to copy.");
    return;
  }
  const text = JSON.stringify(state.packetResponse.packet, null, 2);
  await navigator.clipboard.writeText(text);
  log("Copied model-visible packet JSON.");
}

function render() {
  const selected = state.packetResponse?.selected_ids || [];
  const confidence = normalizeConfidence(state.packetResponse?.confidence || 0);
  els.memoryCount.textContent = String(state.health?.memory_count ?? state.memories.length);
  els.selectedCount.textContent = String(selected.length);
  els.confidence.textContent = `${confidence}%`;
  els.latency.textContent = state.packetResponse?.latency_ms ? `${Number(state.packetResponse.latency_ms).toFixed(2)} ms` : "-";
  els.routeId.textContent = state.packetResponse?.route_id || "no route";

  if (state.packetResponse) {
    els.routeSummary.textContent = `${state.packetResponse.decision} via ${state.packetResponse.strategy}; selected ${selected.length} item(s).`;
  } else {
    els.routeSummary.textContent = "No packet built yet.";
  }

  renderEvidence();
  renderMemories();
  renderSearchResults();
  els.packetJson.textContent = JSON.stringify(state.packetResponse?.packet || {}, null, 2);
  els.proofJson.textContent = JSON.stringify(state.proofResponse?.route_proof || state.proofResponse || {}, null, 2);
}

function renderEvidence() {
  const evidence = state.packetResponse?.packet?.evidence || [];
  if (!evidence.length) {
    setListEmpty(els.evidenceList, "No evidence admitted yet.");
    return;
  }
  els.evidenceList.classList.remove("empty");
  els.evidenceList.replaceChildren(...evidence.map((item) => itemCard({
    title: item.id,
    body: item.text || "",
    pills: [
      item.source_family,
      item.authority,
      item.staleness,
      `${item.text_policy || "text"}`,
    ].filter(Boolean),
  })));
}

function renderMemories() {
  if (!state.memories.length) {
    setListEmpty(els.memoryList, "No memories loaded.");
    return;
  }
  els.memoryList.classList.remove("empty");
  els.memoryList.replaceChildren(...state.memories.map((item) => itemCard({
    title: item.id,
    body: item.text_preview || item.text || "",
    pills: [
      item.source_family,
      item.authority,
      item.staleness,
      ...(item.tags || []).slice(0, 4),
    ].filter(Boolean),
    onClick: () => {
      els.forgetInput.value = item.id;
      els.searchInput.value = item.id;
    },
  })));
}

function renderSearchResults() {
  if (!state.searchResults.length) {
    setListEmpty(els.searchResults, "No search results.");
    return;
  }
  els.searchResults.classList.remove("empty");
  els.searchResults.replaceChildren(...state.searchResults.map((item) => itemCard({
    title: item.id,
    body: item.text_preview || item.text || "",
    pills: [`score ${item.score ?? "-"}`, item.source_family, item.authority].filter(Boolean),
  })));
}

function itemCard({ title, body, pills, onClick }) {
  const root = document.createElement("article");
  root.className = "item";
  if (onClick) {
    root.tabIndex = 0;
    root.addEventListener("click", onClick);
  }
  const h3 = document.createElement("h3");
  h3.textContent = title;
  const p = document.createElement("p");
  p.textContent = body;
  const meta = document.createElement("div");
  meta.className = "meta";
  for (const pillText of pills || []) {
    const pill = document.createElement("span");
    pill.className = `pill ${pillText === "current" || pillText === "high" ? "good" : ""}`;
    pill.textContent = pillText;
    meta.appendChild(pill);
  }
  root.append(h3, p, meta);
  return root;
}

function setListEmpty(node, text) {
  node.className = "list empty";
  node.textContent = text;
}

async function requestJson(path, init = {}) {
  const response = await fetch(`${state.apiBase}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers || {}),
    },
  });
  const text = await response.text();
  let json = {};
  try {
    json = text ? JSON.parse(text) : {};
  } catch (error) {
    throw new Error(`${response.status} ${response.statusText}: non-JSON response`);
  }
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}: ${json.error || text}`);
  }
  return json;
}

async function runBusy(task, failureLabel) {
  setBusy(true);
  try {
    await task();
  } catch (error) {
    setOnline(false, "Offline or request failed");
    log(`${failureLabel}: ${error.message || String(error)}`);
  } finally {
    setBusy(false);
    render();
  }
}

function setBusy(value) {
  state.busy = value;
  document.querySelectorAll("button").forEach((button) => {
    button.disabled = value;
  });
}

function setOnline(isOnline, text) {
  els.statusDot.classList.toggle("online", isOnline);
  els.statusDot.classList.toggle("offline", !isOnline);
  els.statusText.textContent = text;
}

function log(message) {
  const time = new Date().toLocaleTimeString();
  els.log.textContent = `[${time}] ${message}\n${els.log.textContent}`;
}

function splitCsv(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeBase(value) {
  return String(value || DEFAULT_API_BASE).replace(/\/+$/, "");
}

function normalizeConfidence(value) {
  const number = Number(value || 0);
  const percent = number <= 1 ? number * 100 : number;
  return Math.max(0, Math.min(100, Math.round(percent)));
}

const ALEXANDRIA_SEED_ITEMS = [
  {
    id: "alexandria_simple_hook_boundary",
    text: "Alexandria Simple is a no-build frontend that talks directly to the D-ACCA hook service. It uses /health, /hooks, /memories, /ingest, /packet, /proof/{route_id}, /search, /feedback, and /forget.",
    source_family: "source_code",
    authority: "high",
    claim_type: "fact",
    tags: ["alexandria", "simple", "hooks", "d-acca"],
    aliases: ["simple frontend", "hook boundary", "same hooks"],
    helper_query: "Alexandria simple frontend same D-ACCA hooks health ingest packet proof feedback",
    guard_terms: ["alexandria", "hooks"],
    replay_match_terms: ["simple frontend", "same hooks", "D-ACCA hooks"],
    distillation_patterns: [["simple", "frontend"], ["same", "hooks"]],
  },
  {
    id: "alexandria_model_packet_rule",
    text: "The model-visible output is the packet object returned by /packet. Route proof is for dashboard debugging and should not be treated as model-visible context by default.",
    source_family: "safety_policy",
    authority: "high",
    claim_type: "policy",
    tags: ["alexandria", "packet", "proof", "model_visible"],
    aliases: ["model packet", "route proof", "debug proof"],
    helper_query: "model-visible packet route proof dashboard debug",
    guard_terms: ["packet", "proof"],
    replay_match_terms: ["model packet", "proof"],
    distillation_patterns: [["model", "packet"], ["route", "proof"]],
  },
  {
    id: "alexandria_feedback_loop",
    text: "Feedback uses POST /feedback with ratings useful, wrong, stale, missed, private, or neutral. Feedback records route quality without directly editing packet evidence.",
    source_family: "workflow_trace",
    authority: "medium",
    claim_type: "fact",
    tags: ["alexandria", "feedback", "learning"],
    aliases: ["feedback loop", "mark useful", "mark stale"],
    helper_query: "Alexandria feedback loop useful wrong stale missed private",
    guard_terms: ["feedback"],
    replay_match_terms: ["feedback", "useful", "stale"],
    distillation_patterns: [["feedback", "loop"], ["mark", "stale"]],
  },
  {
    id: "alexandria_harness_contract",
    text: "The planned frontend should eventually consume the Alexandria harness view model, but this simple UI deliberately calls the raw hooks so the system can be dogfooded immediately.",
    source_family: "runbook",
    authority: "high",
    claim_type: "fact",
    tags: ["alexandria", "harness", "frontend"],
    aliases: ["planned frontend", "harness view model", "dogfood immediately"],
    helper_query: "planned frontend harness view model simple UI raw hooks dogfood immediately",
    guard_terms: ["harness", "frontend"],
    replay_match_terms: ["planned frontend", "harness", "dogfood"],
    distillation_patterns: [["harness", "view"], ["dogfood", "immediately"]],
  },
];
