import { useEffect, useMemo, useState } from "react";

import { useMutation, useQuery } from "@tanstack/react-query";

import ChatPanel from "./components/ChatPanel";
import ConsentFlowPanel from "./components/ConsentFlowPanel";
import { useHealth } from "./hooks/useHealth";
import {
  fetchAhaCategories,
  fetchAhaFeatures,
  fetchAnalysisSummary,
  fetchConfluencePages,
  fetchCosmosContainers,
  runCosmosAssistant,
  runCosmosDiagnostics,
  syncConfluenceSources,
} from "./services/api";

function stripHtml(value: string): string {
  const withLineBreaks = value
    .replace(/<\s*br\s*\/?>/gi, "\n")
    .replace(/<\s*\/p\s*>/gi, "\n\n")
    .replace(/<\s*li\s*>/gi, "- ")
    .replace(/<[^>]+>/g, " ");

  const textarea = document.createElement("textarea");
  textarea.innerHTML = withLineBreaks;
  return textarea.value.replace(/\s+\n/g, "\n").replace(/\n\s+/g, "\n").replace(/\n{3,}/g, "\n\n").replace(/\s{2,}/g, " ").trim();
}

function normalizeText(value: unknown, fallback: string): string {
  if (typeof value === "string") {
    const trimmed = stripHtml(value.trim());
    return trimmed.length > 0 ? trimmed : fallback;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    const preferredKeys = ["name", "title", "body", "text", "value", "label"];

    for (const key of preferredKeys) {
      const nestedValue = record[key];
      if (typeof nestedValue === "string" && nestedValue.trim().length > 0) {
        return nestedValue.trim();
      }
    }

    try {
      return JSON.stringify(value);
    } catch {
      return fallback;
    }
  }

  return fallback;
}

function dedupeByKey<T>(items: T[], getKey: (item: T) => string): T[] {
  const seen = new Set<string>();
  return items.filter((item) => {
    const key = getKey(item);
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function formatUpdatedAt(value?: string | null): string {
  if (!value) {
    return "Last updated unavailable";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "Last updated unavailable";
  }

  return `Last updated ${parsed.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  })}`;
}

function formatDiagnosticsMetric(value: unknown): string {
  if (value == null) {
    return "Unavailable";
  }

  if (typeof value === "string") {
    return value;
  }

  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function isActionableAhaStatus(status: string): boolean {
  return (
    status.includes("not started") ||
    status.includes("progress") ||
    status.includes("review") ||
    status.includes("promoted") ||
    status.includes("planned") ||
    status.includes("backlog")
  );
}

function isCompletedAhaStatus(status: string): boolean {
  return (
    status.includes("shipped") ||
    status.includes("done") ||
    status.includes("complete") ||
    status.includes("closed")
  );
}

const navItemIcons = {
  chat: "💬",
  insights: "📊",
  workspace: "🗂️",
  cosmos: "🔮",
  flow: "🔄",
} as const;

export default function App() {
  const [isSidebarPinned, setIsSidebarPinned] = useState(false);
  const [isSidebarHovered, setIsSidebarHovered] = useState(false);
  const [activeView, setActiveView] = useState<
    "chat" | "insights" | "workspace" | "cosmos" | "flow"
  >("chat");
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [visibleCount, setVisibleCount] = useState(20);
  const [cosmosContainerName, setCosmosContainerName] = useState("");
  const [cosmosLogicalType, setCosmosLogicalType] = useState("");
  const [cosmosPartitionKeyValue, setCosmosPartitionKeyValue] = useState("");
  const [cosmosQueryText, setCosmosQueryText] = useState("SELECT TOP 10 * FROM c");
  const [cosmosMaxItems, setCosmosMaxItems] = useState("10");
  const [performSampleInsert, setPerformSampleInsert] = useState(true);
  const [cleanupAfterInsert, setCleanupAfterInsert] = useState(true);
  const [showDiagnosticsEditor, setShowDiagnosticsEditor] = useState(true);
  const [showDiagnosticsInsertResults, setShowDiagnosticsInsertResults] = useState(false);
  const [showDiagnosticsMetrics, setShowDiagnosticsMetrics] = useState(false);
  const [showDiagnosticsSamples, setShowDiagnosticsSamples] = useState(false);
  const [cosmosAssistantAction, setCosmosAssistantAction] = useState<"prepare_query" | "explain_response" | "recreate_query">("prepare_query");
  const [cosmosAssistantPrompt, setCosmosAssistantPrompt] = useState("");
  const [cosmosInsertScenariosText, setCosmosInsertScenariosText] = useState(`[
  {
    "purpose": "profile_insert",
    "logical_type": "Profile",
    "partition_key_value": "sample-partition-key",
    "payload": {
      "type": "Profile",
      "identifierHash": "sample-partition-key"
    },
    "cleanup_after_insert": true
  }
]`);
  const healthQuery = useHealth();
  const summaryQuery = useQuery({
    queryKey: ["analysis-summary"],
    queryFn: () => fetchAnalysisSummary(7),
  });
  const pagesQuery = useQuery({
    queryKey: ["confluence-pages", "home"],
    queryFn: () => fetchConfluencePages(20),
  });
  const ideasQuery = useQuery({
    queryKey: ["aha-ideas", categoryFilter],
    queryFn: () => fetchAhaFeatures(200, 0, categoryFilter),
  });
  const categoriesQuery = useQuery({
    queryKey: ["aha-categories"],
    queryFn: fetchAhaCategories,
    staleTime: 5 * 60 * 1000,
  });
  const cosmosContainersQuery = useQuery({
    queryKey: ["cosmos-containers"],
    queryFn: fetchCosmosContainers,
    enabled: activeView === "cosmos",
  });
  const cosmosDiagnosticsMutation = useMutation({
    mutationFn: runCosmosDiagnostics,
  });
  const cosmosAssistantMutation = useMutation({
    mutationFn: runCosmosAssistant,
  });
  const syncConfluenceMutation = useMutation({
    mutationFn: (force: boolean) => syncConfluenceSources(force),
  });

  const summary = summaryQuery.data;
  const topKeywords = summary?.top_keywords ?? [];
  const activityTrend = summary?.activity_trend ?? [];
  const pages = pagesQuery.data ?? [];
  const ideas = ideasQuery.data?.items ?? [];
  const ideasTotal = ideasQuery.data?.meta?.total ?? 0;
  const cosmosContainers = cosmosContainersQuery.data ?? [];
  const selectedCosmosContainerName = cosmosContainerName || cosmosContainers[0]?.id || "";
  const selectedCosmosContainer = cosmosContainers.find((container) => container.id === selectedCosmosContainerName);
  const cosmosDiagnostics = cosmosDiagnosticsMutation.data;
  const cosmosAssistant = cosmosAssistantMutation.data;
  const syncActivities = [
    summaryQuery.isFetching ? "Updating dashboard summary" : null,
    pagesQuery.isFetching ? "Fetching Confluence docs" : null,
    ideasQuery.isFetching ? "Fetching Aha signals" : null,
  ].filter((value): value is string => Boolean(value));
  const isSyncing = syncActivities.length > 0;
  const syncStatusLabel = isSyncing ? syncActivities.join(" • ") : "Workspace data is up to date";
  const syncStatusToneClass = isSyncing ? "sync-status-banner-active" : "sync-status-banner-ready";

  useEffect(() => {
    setVisibleCount(20);
  }, [categoryFilter, sourceFilter, statusFilter, search, activeView]);

  const feedItems = useMemo(() => {
    const pageItems = dedupeByKey(
      pages.map((page) => ({
      id: `page-${page.id}`,
      title: normalizeText(page.title, page.id),
      subtitle:
        typeof page.space_key === "string" && page.space_key.trim().length > 0
          ? `Confluence · ${page.space_key}`
          : "Confluence document",
      description: normalizeText(
        page.excerpt,
        "Relevant technical or functional guidance from Confluence."
      ),
      badge: formatUpdatedAt(page.updated_at),
      priority: "Reference",
      source: "confluence",
      actionLabel: "Open doc",
      url: page.url,
      status: "indexed",
      category: "Reference documentation",
      updatedAt: page.updated_at ?? null,
    })),
      (page) => `${page.source}:${page.url ?? ""}:${page.title.toLowerCase()}`
    );

    const featureItems = dedupeByKey(
      ideas.map((feature) => ({
      id: `feature-${feature.id}`,
      title: normalizeText(feature.name, feature.id),
      subtitle:
        normalizeText(feature.reference_num, "") !== ""
          ? `Aha idea · ${normalizeText(feature.reference_num, "")}`
          : "Aha idea",
      description: normalizeText(
        feature.description,
        "Consent management work item synchronized from Aha."
      ),
      badge: normalizeText(feature.priority, "Medium"),
      priority: normalizeText(feature.priority, "Medium"),
      source: "aha",
      actionLabel: "Open idea",
      url: feature.url,
      status: normalizeText(feature.status, "Not started").toLowerCase(),
      category: normalizeText(feature.category, "Consent Management"),
      updatedAt: null,
    })),
      (feature) =>
        [
          feature.source,
          feature.subtitle.toLowerCase(),
          feature.title.toLowerCase(),
          feature.url ?? "",
        ].join(":"),
    );

    return [...featureItems, ...pageItems];
  }, [ideas, pages]);

  const filteredItems = useMemo(() => {
    const baseItems = feedItems.filter((item) => {
      const matchesView =
        activeView === "insights"
          ? item.source === "aha"
          : activeView === "workspace"
            ? item.source === "confluence"
            : true;
      const matchesSearch =
        search.trim().length === 0 ||
        [item.title, item.subtitle, item.description, item.badge]
          .join(" ")
          .toLowerCase()
          .includes(search.toLowerCase());
      const matchesSource = sourceFilter === "all" || item.source === sourceFilter;
      const matchesStatus =
        statusFilter === "all" || item.status.includes(statusFilter.toLowerCase());
      const matchesCategory =
        categoryFilter === "all" || item.source !== "aha" || item.category === categoryFilter;
      return matchesView && matchesSearch && matchesSource && matchesStatus && matchesCategory;
    });

    const sortedByRecent = [...baseItems].sort((left, right) => {
      const leftTime = left.updatedAt ? new Date(left.updatedAt).getTime() : 0;
      const rightTime = right.updatedAt ? new Date(right.updatedAt).getTime() : 0;
      return rightTime - leftTime;
    });

    return sortedByRecent;
  }, [activeView, feedItems, search, sourceFilter, statusFilter, categoryFilter]);

  const ahaCategories = categoriesQuery.data ?? [];
  const awaitingCount = feedItems.filter((item) => item.source === "aha").length;
  const referenceCount = feedItems.filter((item) => item.source === "confluence").length;
  const trendMax = Math.max(...activityTrend.map((item) => item.value), 1);
  const trendPoints = activityTrend
    .map((item, index) => {
      if (activityTrend.length === 1) {
        return `20,90`;
      }
      const x = 20 + (index * 280) / (activityTrend.length - 1);
      const y = 90 - (item.value / trendMax) * 70;
      return `${x},${y}`;
    })
    .join(" ");
  const isCosmosView = activeView === "cosmos";
  const isChatView = activeView === "chat";
  const isFlowView = activeView === "flow";
  const isDiagnosticsView = isCosmosView || isFlowView;
  const isAssistantView = isChatView;
  const sectionTitle =
    activeView === "chat"
      ? "AI Consent Assistant"
      : activeView === "insights"
        ? "Product Insights"
        : activeView === "workspace"
          ? "Knowledge Workspace"
          : activeView === "cosmos"
            ? "Cosmos Diagnostics"
            : activeView === "flow"
              ? "Consent Flow Explorer"
              : "Overview";
  const sectionDescription =
    activeView === "chat"
      ? "Ask questions about consent implementation, compliance, and technical architecture."
      : activeView === "insights"
        ? "Review product signals, features, and development progress from Aha."
        : activeView === "workspace"
          ? "Browse technical documentation and implementation guides from Confluence."
          : activeView === "cosmos"
            ? "Analyze Cosmos DB performance, query optimization, and data modeling."
            : activeView === "flow"
              ? "Explore the end-to-end consent receipt ingestion pipeline with AI-powered Q&A."
              : "Comprehensive overview of consent management workspace.";
  const chatContextTitle =
    activeView === "chat"
      ? "AI Assistant context"
      : activeView === "insights"
        ? "Product insights context"
        : activeView === "workspace"
          ? "Knowledge workspace context"
          : "Cosmos diagnostics context";
  const chatContextHint =
    activeView === "workspace"
      ? "Focus on technical documentation and implementation guides"
      : activeView === "insights"
        ? "Focus on product features and development signals"
        : activeView === "chat"
          ? "Use AI to answer consent management questions"
          : "Use active filters and currently visible items";

  const handleViewChange = (
    view: "chat" | "insights" | "workspace" | "cosmos" | "flow"
  ) => {
    setActiveView(view);
    setSearch("");
    setStatusFilter("all");

    if (view === "workspace") {
      setSourceFilter("confluence");
      return;
    }

    if (view === "insights") {
      setSourceFilter("aha");
      return;
    }

    setSourceFilter("all");
  };

  const handleRunCosmosDiagnostics = () => {
    if (!selectedCosmosContainerName) {
      return;
    }

    let insertScenarios: Array<{
      purpose: string;
      payload: Record<string, unknown>;
      partition_key_value?: string | null;
      logical_type?: string | null;
      cleanup_after_insert?: boolean | null;
    }> = [];

    if (cosmosInsertScenariosText.trim().length > 0) {
      try {
        const parsed = JSON.parse(cosmosInsertScenariosText) as unknown;
        insertScenarios = Array.isArray(parsed) ? parsed as Array<{
          purpose: string;
          payload: Record<string, unknown>;
          partition_key_value?: string | null;
          logical_type?: string | null;
          cleanup_after_insert?: boolean | null;
        }> : [];
      } catch {
        cosmosDiagnosticsMutation.reset();
        return;
      }
    }

    cosmosDiagnosticsMutation.mutate({
      container_name: selectedCosmosContainerName,
      query_text: cosmosQueryText,
      partition_key_value: cosmosPartitionKeyValue.trim() || null,
      logical_type: cosmosLogicalType.trim() || null,
      max_items: Number.parseInt(cosmosMaxItems, 10) || 10,
      perform_sample_insert: performSampleInsert,
      cleanup_after_insert: cleanupAfterInsert,
      insert_scenarios: insertScenarios,
    });
  };

  const handleRunCosmosAssistant = () => {
    if (!selectedCosmosContainerName || !cosmosAssistantPrompt.trim()) {
      return;
    }

    cosmosAssistantMutation.mutate({
      action: cosmosAssistantAction,
      prompt: cosmosAssistantPrompt.trim(),
      container_name: selectedCosmosContainerName,
      logical_type: cosmosLogicalType.trim() || null,
      partition_key_field: cosmosDiagnostics?.partition_key_field ?? selectedCosmosContainer?.partition_key_paths?.[0] ?? null,
      partition_key_value: cosmosPartitionKeyValue.trim() || null,
      current_query: cosmosQueryText,
      diagnostics_result: cosmosDiagnostics ? (cosmosDiagnostics as unknown as Record<string, unknown>) : null,
    });
  };

  const handleApplySuggestedQuery = () => {
    if (cosmosAssistant?.suggested_query) {
      setCosmosQueryText(cosmosAssistant.suggested_query);
    }
  };

  const isSidebarExpanded = isSidebarPinned || isSidebarHovered;

  return (
    <div className={`app-shell ${isSidebarExpanded ? "app-shell-sidebar-expanded" : "app-shell-sidebar-collapsed"}`}>
      <aside
        className={`sidebar ${isSidebarExpanded ? "sidebar-expanded" : "sidebar-collapsed"}`}
        onMouseEnter={() => setIsSidebarHovered(true)}
        onMouseLeave={() => setIsSidebarHovered(false)}
      >
        <div className="brand-mark">🤖 CM</div>
        <button
          className="sidebar-toggle"
          type="button"
          onClick={() => setIsSidebarPinned((current) => !current)}
          aria-label={isSidebarPinned ? "Unpin navigation" : "Pin navigation"}
        >
          {isSidebarPinned ? "Unpin" : "Pin"}
        </button>
        <nav className="sidebar-nav" aria-label="Primary">
          <button
            className={`nav-item ${activeView === "chat" ? "nav-item-active" : ""}`}
            onClick={() => handleViewChange("chat")}
            type="button"
          >
            <span className="nav-item-icon" aria-hidden="true">{navItemIcons.chat}</span>
            <span className="nav-item-label">AI Assistant</span>
          </button>
          <button
            className={`nav-item ${activeView === "insights" ? "nav-item-active" : ""}`}
            onClick={() => handleViewChange("insights")}
            type="button"
          >
            <span className="nav-item-icon" aria-hidden="true">{navItemIcons.insights}</span>
            <span className="nav-item-label">Product Insights</span>
          </button>
          <button
            className={`nav-item ${activeView === "workspace" ? "nav-item-active" : ""}`}
            onClick={() => handleViewChange("workspace")}
            type="button"
          >
            <span className="nav-item-icon" aria-hidden="true">{navItemIcons.workspace}</span>
            <span className="nav-item-label">Knowledge</span>
          </button>
          <button
            className={`nav-item ${activeView === "cosmos" ? "nav-item-active" : ""}`}
            onClick={() => handleViewChange("cosmos")}
            type="button"
          >
            <span className="nav-item-icon" aria-hidden="true">{navItemIcons.cosmos}</span>
            <span className="nav-item-label">Cosmos</span>
          </button>
          <button
            className={`nav-item ${activeView === "flow" ? "nav-item-active" : ""}`}
            onClick={() => handleViewChange("flow")}
            type="button"
          >
            <span className="nav-item-icon" aria-hidden="true">{navItemIcons.flow}</span>
            <span className="nav-item-label">Flow</span>
          </button>
        </nav>
      </aside>

      <main className="workspace">
        <header className="product-bar">
          <div className="product-brand">
            <span className="product-brand-name">🤖 Consent Management AI</span>
            <span className="product-brand-divider">/</span>
            <span className="product-brand-page">Intelligent Workspace</span>
          </div>
        </header>

        <header className="topbar">
          <div>
            <h1>{sectionTitle}</h1>
          </div>
          <div className="topbar-actions">
            <button 
              className="ghost-button" 
              type="button"
              onClick={() => syncConfluenceMutation.mutate(true)}
              disabled={syncConfluenceMutation.isPending}
            >
              {syncConfluenceMutation.isPending ? "Refreshing..." : "Refresh sources"}
            </button>
            <span className={`status-pill ${healthQuery.data ? "status-pill-live" : "status-pill-down"}`}>
              {healthQuery.data ? `API ${healthQuery.data.status}` : "API unavailable"}
            </span>
          </div>
        </header>

        <section className="toolbar-strip">
          <button className="toolbar-filter">Workspace name: Consent Management</button>
          <button className="toolbar-filter">Source categories: Any</button>
          <button className="toolbar-filter">Source status: Any</button>
          <button className="toolbar-filter">Sources: Aha + Confluence</button>
        </section>

        <section className={`sync-status-banner ${syncStatusToneClass}`} aria-live="polite">
          <div>
            <strong>{isSyncing ? "Source sync in progress" : "Source sync status"}</strong>
            <span>{syncStatusLabel}</span>
          </div>
          <span className="sync-status-meta">
            {isSyncing ? "Refreshing indexed workspace data" : "Indexed sources ready"}
          </span>
        </section>

        {isFlowView ? (
          <div className="cf-view-container">
            <ConsentFlowPanel />
          </div>
        ) : isChatView ? (
          <div className="chat-main-container">
            <ChatPanel
              contextTitle={chatContextTitle}
              contextHint={chatContextHint}
              onClose={() => handleViewChange("workspace")}
            />
          </div>
        ) : isCosmosView ? (
          <>
            <section className="cosmos-diagnostics-grid">
              <article className="card-elevated cosmos-editor-panel">
                <div className="panel-header compact-panel-header">
                  <div>
                    <h2>Query editor</h2>
                    <p className="muted">Use container + logical type together for shared Cosmos stores. This matches the container/type model from your consent flow note.</p>
                  </div>
                  <button className="ghost-button" type="button" onClick={() => setShowDiagnosticsEditor((current) => !current)}>
                    {showDiagnosticsEditor ? "Hide editor" : "Show editor"}
                  </button>
                </div>
                {showDiagnosticsEditor ? <div className="cosmos-editor-form">
                  <label className="cosmos-field">
                    <span>Container</span>
                    <select value={selectedCosmosContainerName} onChange={(event) => setCosmosContainerName(event.target.value)}>
                      {cosmosContainers.map((container) => (
                        <option key={container.id} value={container.id}>{container.id}</option>
                      ))}
                    </select>
                  </label>
                  <label className="cosmos-field">
                    <span>Logical type</span>
                    <input value={cosmosLogicalType} onChange={(event) => setCosmosLogicalType(event.target.value)} className="filter-input" placeholder="Profile, DataSubjectAccessToken, LinkedIdentityGroup..." />
                  </label>
                  <label className="cosmos-field">
                    <span>Partition key value</span>
                    <input value={cosmosPartitionKeyValue} onChange={(event) => setCosmosPartitionKeyValue(event.target.value)} className="filter-input" placeholder="identifierHash / token / other partition key" />
                  </label>
                  <label className="cosmos-field">
                    <span>Max items</span>
                    <input value={cosmosMaxItems} onChange={(event) => setCosmosMaxItems(event.target.value)} className="filter-input" placeholder="10" />
                  </label>
                  <label className="cosmos-field cosmos-field-full">
                    <span>Cosmos SQL query</span>
                    <textarea value={cosmosQueryText} onChange={(event) => setCosmosQueryText(event.target.value)} className="cosmos-query-input" rows={8} />
                  </label>
                  <label className="cosmos-field cosmos-field-full">
                    <span>Insert scenarios JSON</span>
                    <textarea value={cosmosInsertScenariosText} onChange={(event) => setCosmosInsertScenariosText(event.target.value)} className="cosmos-query-input" rows={12} />
                  </label>
                  <label className="cosmos-checkbox">
                    <input type="checkbox" checked={performSampleInsert} onChange={(event) => setPerformSampleInsert(event.target.checked)} />
                    <span>Clone first sampled document into a new insert and measure write RU</span>
                  </label>
                  <label className="cosmos-checkbox">
                    <input type="checkbox" checked={cleanupAfterInsert} onChange={(event) => setCleanupAfterInsert(event.target.checked)} />
                    <span>Delete inserted sample after measurement</span>
                  </label>
                  <div className="cosmos-actions">
                    <button className="primary-toolbar-button" type="button" onClick={handleRunCosmosDiagnostics} disabled={!selectedCosmosContainerName || cosmosDiagnosticsMutation.isPending}>
                      {cosmosDiagnosticsMutation.isPending ? "Running diagnostics..." : "Run diagnostics"}
                    </button>
                  </div>
                </div> : null}
                {cosmosContainersQuery.isError ? <p className="error">Unable to load Cosmos containers. Check Cosmos configuration first.</p> : null}
                {selectedCosmosContainer ? (
                  <div className="cosmos-container-meta">
                    <span className="chip">Partition key: {selectedCosmosContainer.partition_key_paths.join(", ") || "None"}</span>
                    <span className="chip">Default TTL: {selectedCosmosContainer.default_ttl ?? "Not set"}</span>
                    <span className="chip">Analytical TTL: {selectedCosmosContainer.analytical_storage_ttl ?? "Not set"}</span>
                  </div>
                ) : null}
                <div className="comment-card cosmos-assistant-panel">
                  <strong>AI query assistant</strong>
                  <p className="muted">Ask AI to prepare a query, explain the current diagnostics response, or recreate a better next query from the current result.</p>
                  <div className="cosmos-assistant-actions">
                    <button className={`tab ${cosmosAssistantAction === "prepare_query" ? "tab-active" : ""}`} type="button" onClick={() => setCosmosAssistantAction("prepare_query")}>
                      Prepare query
                    </button>
                    <button className={`tab ${cosmosAssistantAction === "explain_response" ? "tab-active" : ""}`} type="button" onClick={() => setCosmosAssistantAction("explain_response")}>
                      Explain response
                    </button>
                    <button className={`tab ${cosmosAssistantAction === "recreate_query" ? "tab-active" : ""}`} type="button" onClick={() => setCosmosAssistantAction("recreate_query")}>
                      Recreate query
                    </button>
                  </div>
                  <textarea
                    value={cosmosAssistantPrompt}
                    onChange={(event) => setCosmosAssistantPrompt(event.target.value)}
                    className="cosmos-query-input cosmos-assistant-input"
                    rows={4}
                    placeholder="Example: Create a query for active Profile documents with high RU risk, or explain why this response consumed so many RUs."
                  />
                  <div className="cosmos-assistant-toolbar">
                    <button className="primary-toolbar-button" type="button" onClick={handleRunCosmosAssistant} disabled={!selectedCosmosContainerName || !cosmosAssistantPrompt.trim() || cosmosAssistantMutation.isPending}>
                      {cosmosAssistantMutation.isPending ? "Thinking..." : "Ask AI"}
                    </button>
                    {cosmosAssistant?.suggested_query ? (
                      <button className="ghost-button" type="button" onClick={handleApplySuggestedQuery}>
                        Apply suggested query
                      </button>
                    ) : null}
                  </div>
                  {cosmosAssistantMutation.isError ? (
                    <p className="error">{cosmosAssistantMutation.error instanceof Error ? cosmosAssistantMutation.error.message : "Failed to run Cosmos assistant"}</p>
                  ) : null}
                  {cosmosAssistant ? (
                    <div className="cosmos-assistant-response">
                      <pre className="cosmos-json-view">{cosmosAssistant.answer}</pre>
                      {cosmosAssistant.suggested_query ? (
                        <div className="cosmos-diagnostics-metric-block">
                          <span className="muted">Suggested query</span>
                          <pre className="cosmos-json-view">{cosmosAssistant.suggested_query}</pre>
                        </div>
                      ) : null}
                      {cosmosAssistant.follow_up_questions.length > 0 ? (
                        <div className="cosmos-diagnostics-metric-block">
                          <span className="muted">Suggested follow-ups</span>
                          <ul className="insight-list">
                            {cosmosAssistant.follow_up_questions.map((question) => (
                              <li key={question}>{question}</li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              </article>

              <article className="card-elevated cosmos-results-panel">
                <div className="panel-header compact-panel-header">
                  <div>
                    <h2>Diagnostics output</h2>
                    <p className="muted">Measure query RU, sample write RU, index footprint, and estimated headroom toward the 2 MB document limit.</p>
                  </div>
                </div>
                {cosmosDiagnosticsMutation.isError ? (
                  <p className="error">{cosmosDiagnosticsMutation.error instanceof Error ? cosmosDiagnosticsMutation.error.message : "Failed to run Cosmos diagnostics"}</p>
                ) : null}
                {!cosmosDiagnostics ? (
                  <p className="muted">Run a diagnostics query to inspect request charge, indexing signals, sample sizes, and tuning options.</p>
                ) : (
                  <div className="cosmos-results-stack">
                    <div className="cosmos-metric-grid">
                      <div className="comment-card">
                        <strong>Query RU</strong>
                        <p className="muted">{cosmosDiagnostics.query_metrics.request_charge.toFixed(2)} RU</p>
                      </div>
                      <div className="comment-card">
                        <strong>Latency</strong>
                        <p className="muted">{cosmosDiagnostics.query_metrics.duration_ms.toFixed(2)} ms</p>
                      </div>
                      <div className="comment-card">
                        <strong>Results</strong>
                        <p className="muted">{cosmosDiagnostics.result_count} documents</p>
                      </div>
                      <div className="comment-card">
                        <strong>Largest sample</strong>
                        <p className="muted">{cosmosDiagnostics.size_estimate.largest_document_bytes.toLocaleString()} bytes</p>
                      </div>
                    </div>

                    <div className="cosmos-metric-grid">
                      <div className="comment-card">
                        <strong>Included index paths</strong>
                        <p className="muted">{cosmosDiagnostics.index_summary.included_path_count}</p>
                      </div>
                      <div className="comment-card">
                        <strong>Excluded index paths</strong>
                        <p className="muted">{cosmosDiagnostics.index_summary.excluded_path_count}</p>
                      </div>
                      <div className="comment-card">
                        <strong>Composite indexes</strong>
                        <p className="muted">{cosmosDiagnostics.index_summary.composite_index_count}</p>
                      </div>
                      <div className="comment-card">
                        <strong>2 MB headroom</strong>
                        <p className="muted">{cosmosDiagnostics.size_estimate.remaining_bytes_to_two_mb_for_largest_document.toLocaleString()} bytes</p>
                      </div>
                    </div>

                    <div className="cosmos-section-toggle-row">
                      <button className="ghost-button" type="button" onClick={() => setShowDiagnosticsInsertResults((current) => !current)}>
                        {showDiagnosticsInsertResults ? "Hide insert results" : "Show insert results"}
                      </button>
                      <button className="ghost-button" type="button" onClick={() => setShowDiagnosticsMetrics((current) => !current)}>
                        {showDiagnosticsMetrics ? "Hide metrics" : "Show metrics"}
                      </button>
                      <button className="ghost-button" type="button" onClick={() => setShowDiagnosticsSamples((current) => !current)}>
                        {showDiagnosticsSamples ? "Hide sample docs" : "Show sample docs"}
                      </button>
                    </div>

                    {showDiagnosticsInsertResults && cosmosDiagnostics.insert_metrics ? (
                      <div className="comment-card">
                        <strong>Sample insert measurement</strong>
                        <p className="muted">Status: {cosmosDiagnostics.insert_metrics.status}</p>
                        <p className="muted">Source item id: {cosmosDiagnostics.insert_metrics.source_item_id ?? "Unavailable"}</p>
                        <p className="muted">Source item type: {cosmosDiagnostics.insert_metrics.source_item_type ?? "Unavailable"}</p>
                        <p className="muted">Inserted item id: {cosmosDiagnostics.insert_metrics.item_id ?? "Unavailable"}</p>
                        <p className="muted">Partition key field: {cosmosDiagnostics.insert_metrics.partition_key_field ?? "Unavailable"}</p>
                        <p className="muted">Partition key value: {cosmosDiagnostics.insert_metrics.partition_key_value ?? "Unavailable"}</p>
                        <p className="muted">Insert RU: {cosmosDiagnostics.insert_metrics.request_charge.toFixed(2)} RU</p>
                        <p className="muted">Cleanup RU: {cosmosDiagnostics.insert_metrics.delete_request_charge.toFixed(2)} RU</p>
                        <div className="cosmos-diagnostics-metric-block">
                          <span className="muted">Inserted document payload</span>
                          <pre className="cosmos-json-view">{formatDiagnosticsMetric(cosmosDiagnostics.insert_metrics.inserted_document)}</pre>
                        </div>
                        <div className="cosmos-diagnostics-metric-block">
                          <span className="muted">Create response headers</span>
                          <pre className="cosmos-json-view">{formatDiagnosticsMetric(cosmosDiagnostics.insert_metrics.create_response_headers)}</pre>
                        </div>
                        <div className="cosmos-diagnostics-metric-block">
                          <span className="muted">Delete response headers</span>
                          <pre className="cosmos-json-view">{formatDiagnosticsMetric(cosmosDiagnostics.insert_metrics.delete_response_headers)}</pre>
                        </div>
                      </div>
                    ) : null}

                    {showDiagnosticsInsertResults && cosmosDiagnostics.insert_scenarios.length > 0 ? (
                      <div className="comment-card">
                        <strong>Purpose-based insert scenarios</strong>
                        {cosmosDiagnostics.insert_scenarios.map((scenario) => (
                          <div key={`${scenario.purpose ?? "scenario"}-${scenario.item_id ?? "no-id"}`} className="cosmos-diagnostics-metric-block">
                            <p className="muted">Purpose: {scenario.purpose ?? "Unavailable"}</p>
                            <p className="muted">Status: {scenario.status}</p>
                            <p className="muted">Insert RU: {scenario.request_charge.toFixed(2)} RU</p>
                            <p className="muted">Cleanup RU: {scenario.delete_request_charge.toFixed(2)} RU</p>
                            <p className="muted">Partition key value: {scenario.partition_key_value ?? "Unavailable"}</p>
                            <pre className="cosmos-json-view">{formatDiagnosticsMetric(scenario.inserted_document)}</pre>
                          </div>
                        ))}
                      </div>
                    ) : null}

                    <div className="comment-card">
                      <strong>Tuning recommendations</strong>
                      <ul className="insight-list">
                        {cosmosDiagnostics.tuning_recommendations.map((recommendation) => (
                          <li key={recommendation}>{recommendation}</li>
                        ))}
                      </ul>
                    </div>

                    {showDiagnosticsMetrics ? <div className="comment-card">
                      <strong>Query + index diagnostics</strong>
                      <p className="muted">Activity id: {cosmosDiagnostics.query_metrics.activity_id ?? "Unavailable"}</p>
                      <div className="cosmos-diagnostics-metric-block">
                        <span className="muted">Query metrics</span>
                        <pre className="cosmos-json-view">{formatDiagnosticsMetric(cosmosDiagnostics.query_metrics.query_metrics)}</pre>
                      </div>
                      <div className="cosmos-diagnostics-metric-block">
                        <span className="muted">Index metrics</span>
                        <pre className="cosmos-json-view">{formatDiagnosticsMetric(cosmosDiagnostics.query_metrics.index_metrics)}</pre>
                      </div>
                    </div> : null}

                    {showDiagnosticsSamples ? <div className="comment-card">
                      <strong>Sample documents</strong>
                      <pre className="cosmos-json-view">{JSON.stringify(cosmosDiagnostics.sample_documents, null, 2)}</pre>
                    </div> : null}
                  </div>
                )}
              </article>
            </section>

            <section className="bottom-grid">
              <article className="card-elevated insight-card">
                <h2>Shared-container reminders</h2>
                <div className="comment-card">
                  <strong>Container + type both matter</strong>
                  <p className="muted">For containers like `consent-datasubjects` and `consent-tokens`, compare RU with and without the logical `type` filter. The same physical container may host multiple document families.</p>
                </div>
                <div className="comment-card">
                  <strong>Compare read vs write cost</strong>
                  <p className="muted">Use sample insert RU to understand how indexing policy and document size affect write amplification, not just query cost.</p>
                </div>
              </article>

              <article className="card-elevated insight-card">
                <h2>Other options</h2>
                <div className="comment-card">
                  <strong>Next diagnostics to add</strong>
                  <p className="muted">Partition fan-out comparison, projected-column vs `SELECT *` comparison, repeated query baselines, and anomaly flags for missing partition-key filters are good next steps.</p>
                </div>
              </article>

              <aside className="side-panel">
                <article className="card-elevated insight-card">
                  <h2>Cosmos guidance</h2>
                  <p className="muted">Best results come when you test the same container with:</p>
                  <ul className="insight-list">
                    <li>no type filter</li>
                    <li>with type filter</li>
                    <li>with partition key</li>
                    <li>narrower projections instead of `SELECT *`</li>
                  </ul>
                </article>
              </aside>
            </section>
          </>
        ) : null}

        {!isDiagnosticsView ? <section className="overview-grid">
          <section className="ideas-table-panel card-elevated">
            <div className="ideas-tabs">
              <button className="tab tab-active" type="button">
                Recent
              </button>
            </div>

            <div className="panel-header compact-panel-header">
              <div>
                <h2>
                  {activeView === "workspace"
                    ? "Knowledge base"
                    : activeView === "chat"
                      ? "Assistant-ready context"
                      : "Sourced items"}
                </h2>
                <p className="muted">{sectionDescription}</p>
              </div>
              <div className="feed-filters">
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  className="filter-input"
                  placeholder="Search sourced issues, records, docs..."
                />
                <select value={sourceFilter} onChange={(event) => setSourceFilter(event.target.value)}>
                  <option value="all">All sources</option>
                  <option value="aha">Aha ideas</option>
                  <option value="confluence">Confluence docs</option>
                </select>
                <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                  <option value="all">All states</option>
                  <option value="not started">Not started</option>
                  <option value="in progress">In progress</option>
                  <option value="indexed">Indexed</option>
                </select>
                {(sourceFilter === "aha" || activeView === "insights") && (
                  <select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
                    <option value="all">All categories</option>
                    {ahaCategories.map((cat) => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                )}
              </div>
            </div>

            <div className="ideas-table-wrap">
              <div className="ideas-table-header ideas-table-row">
                <span>Name</span>
                <span>Category</span>
                <span>Status</span>
                <span>Source</span>
              </div>

              {summaryQuery.isLoading || pagesQuery.isLoading || ideasQuery.isLoading ? (
                <article className="feed-card compact-card">
                  <p className="muted">Loading indexed consent signals...</p>
                </article>
              ) : null}

              {summaryQuery.isError || pagesQuery.isError || ideasQuery.isError ? (
                <article className="feed-card compact-card">
                  <p className="error">Unable to load dashboard data right now.</p>
                </article>
              ) : null}

              {filteredItems.slice(0, visibleCount).map((item) => (
                <article key={item.id} className="ideas-table-row ideas-data-row">
                  <div>
                    <a
                      className="idea-link"
                      href={item.url || "#"}
                      target={item.url ? "_blank" : undefined}
                      rel={item.url ? "noreferrer" : undefined}
                    >
                      {item.title}
                    </a>
                    <p className="ideas-row-description">{item.description}</p>
                    {item.source === "confluence" ? (
                      <p className="ideas-row-meta">{item.badge}</p>
                    ) : null}
                  </div>
                  <span className="table-badge table-badge-category">
                    {item.category}
                  </span>
                  <span className="table-badge table-badge-status">
                    {item.source === "aha" ? item.status.replace(/(^\w|\s\w)/g, (match) => match.toUpperCase()) : "Indexed"}
                  </span>
                  <span className="table-source">{item.source === "aha" ? "Aha" : "Confluence"}</span>
                </article>
              ))}

              {!summaryQuery.isLoading && filteredItems.length === 0 ? (
                <article className="feed-card compact-card">
                  <p className="muted">No items match your current filters.</p>
                </article>
              ) : null}

              {filteredItems.length > visibleCount && (
                <div className="load-more-row">
                  <button
                    type="button"
                    className="load-more-btn"
                    onClick={() => setVisibleCount((n) => n + 20)}
                  >
                    Load {Math.min(20, filteredItems.length - visibleCount)} more
                    <span className="load-more-count">{filteredItems.length - visibleCount} remaining</span>
                  </button>
                </div>
              )}
            </div>
          </section>

          {isAssistantView ? (
            <div className="assistant-column">
              <article className="trend-panel card-elevated assistant-focus-panel">
                <h2>Assistant focus</h2>
                <ul className="insight-list">
                  <li>Summarize sourced consent records into engineering-ready action items.</li>
                  <li>Cross-reference Aha signals with indexed Confluence specifications.</li>
                  <li>Identify rollout, compliance, and edge-case considerations.</li>
                </ul>
              </article>
              {isChatOpen ? (
                <ChatPanel
                  contextTitle={chatContextTitle}
                  contextHint={chatContextHint}
                  onClose={() => setIsChatOpen(false)}
                />
              ) : (
                <article className="card-elevated assistant-launch-card">
                  <h2>Assistant</h2>
                  <p className="muted">Open the assistant to ask questions using the current dashboard context.</p>
                  <button className="primary-toolbar-button" type="button" onClick={() => setIsChatOpen(true)}>
                    Open assistant
                  </button>
                </article>
              )}
            </div>
          ) : (
            <article className="trend-panel card-elevated">
              <div className="trend-header">
                <div>
                  <h2>{awaitingCount} sourced records over the past 30 days</h2>
                  <p className="muted">Synthesized from recent indexed activity</p>
                </div>
                <span className="trend-delta">↘ 44% fewer than previous</span>
              </div>
              <div className="trend-chart">
                <svg viewBox="0 0 320 110" role="img" aria-label="Ideas trend chart">
                  <polyline className="trend-area" points={`20,90 ${trendPoints} 300,90`} />
                  <polyline className="trend-line" points={trendPoints} />
                  {activityTrend.map((item, index) => {
                    const x = activityTrend.length === 1 ? 20 : 20 + (index * 280) / (activityTrend.length - 1);
                    const y = 90 - (item.value / trendMax) * 70;
                    return <circle key={item.label} className="trend-point" cx={x} cy={y} r="3.5" />;
                  })}
                </svg>
                <div className="trend-labels">
                  {activityTrend.map((item) => (
                    <span key={item.label}>{item.label}</span>
                  ))}
                </div>
              </div>
            </article>
          )}
        </section> : null}

        {!isDiagnosticsView ? <section className="bottom-grid">
          <article className="card-elevated insight-card">
            <h2>Recent comments</h2>
            <div className="comment-card">
              <strong>Implementation guidance</strong>
              <p className="muted">Cross-check newly indexed Aha ideas against Confluence specs before promoting to engineering delivery.</p>
            </div>
            <div className="comment-card">
              <strong>Consent review note</strong>
              <p className="muted">Top themes indicate preference-center and opt-out work are currently the highest-signal topics.</p>
            </div>
          </article>

          <article className="card-elevated insight-card">
            <h2>Top themes</h2>
            <div className="chip-row">
              {topKeywords.slice(0, 8).map((item) => (
                <span key={item.keyword} className="chip">{item.keyword}</span>
              ))}
              {topKeywords.length === 0 ? <span className="muted">No keywords yet</span> : null}
            </div>
            <div className="stat-stack">
              <div className="stat-row">
                <span>Indexed docs</span>
                <strong>{String(summary?.total_pages ?? pages.length)}</strong>
              </div>
              <div className="stat-row">
                <span>Consent records</span>
                <strong>{String(summary?.total_features ?? ideasTotal)}</strong>
              </div>
              <div className="stat-row">
                <span>Reference docs</span>
                <strong>{referenceCount}</strong>
              </div>
            </div>
          </article>

          <aside className="side-panel">
            <article className="card-elevated insight-card">
              <h2>Workspace health</h2>
              {healthQuery.isLoading ? <p className="muted">Checking backend health...</p> : null}
              {healthQuery.data ? (
                <>
                  <p className="ok">Backend reachable</p>
                  <p className="muted">{new Date(healthQuery.data.timestamp).toLocaleString()}</p>
                </>
              ) : null}
              {!healthQuery.isLoading && !healthQuery.data ? <p className="error">Backend not reachable</p> : null}
            </article>

            {!isAssistantView ? null : null}
          </aside>
        </section> : null}

        {!isAssistantView && !isDiagnosticsView ? (
          <button
            type="button"
            className="chat-launcher-button"
            onClick={() => setIsChatOpen((current) => !current)}
            aria-label={isChatOpen ? "Close assistant" : "Open assistant"}
          >
            ✦
          </button>
        ) : null}

        {!isAssistantView && !isDiagnosticsView && isChatOpen ? (
          <div className="chat-overlay">
            <div className="chat-overlay-panel">
              <ChatPanel
                contextTitle={chatContextTitle}
                contextHint={chatContextHint}
                onClose={() => setIsChatOpen(false)}
              />
            </div>
          </div>
        ) : null}
      </main>
    </div>
  );
}
