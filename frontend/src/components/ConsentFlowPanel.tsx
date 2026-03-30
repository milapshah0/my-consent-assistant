import React, { Fragment, useState } from "react";

import { useMutation, useQuery } from "@tanstack/react-query";

import {
    type ConsentFlowSection,
    askConsentFlow,
    fetchConsentFlowSections,
    indexConsentFlow,
} from "../services/api";

const FLOW_STAGES = [
  {
    id: "creation",
    label: "Receipt Creation",
    icon: "📥",
    color: "#2563eb",
    bg: "#eff6ff",
    border: "#93c5fd",
    description: "POST /request/v1/consentreceipts",
    sub: "ds-request validates & routes",
    sectionIds: ["receipt-creation-via-ds-request", "call-flow"],
  },
  {
    id: "routing",
    label: "Kafka Routing",
    icon: "⚡",
    color: "#d97706",
    bg: "#fffbeb",
    border: "#fcd34d",
    description: "Topics: consent-receipts / bulkimport",
    sub: "ds-request → Kafka",
    sectionIds: ["ds-request-ds-portal-dsrequestcontroller"],
  },
  {
    id: "ingestion",
    label: "Ingestion",
    icon: "⚙️",
    color: "#7c3aed",
    bg: "#f5f3ff",
    border: "#c4b5fd",
    description: "IngestionService processes receipt",
    sub: "consent-transaction consumers",
    sectionIds: ["consent-transaction-main-app-kafka-consumers"],
  },
  {
    id: "persistence",
    label: "Persistence",
    icon: "💾",
    color: "#059669",
    bg: "#ecfdf5",
    border: "#6ee7b7",
    description: "SQL + Cosmos DB + Blob Storage",
    sub: "consentmanager + ds-preference-cache",
    sectionIds: [
      "consentmanager-main-app-datasubjectupdateconsumer",
      "consentmanager-main-app-datasubjectupdatecosmosparallelconsumer",
      "ds-preference-cache",
      "data-subject-groups-linked-identity-groups",
      "concept",
      "internal-storage-model",
      "how-groups-are-written",
      "read-query-patterns",
    ],
  },
  {
    id: "query",
    label: "Query APIs",
    icon: "🔍",
    color: "#475569",
    bg: "#f8fafc",
    border: "#cbd5e1",
    description: "Public REST APIs for consent data",
    sub: "consent-api / consentmanager",
    sectionIds: [
      "public-api-predicate-params-azure-sql-cosmos-targets",
      "data-subject-apis",
      "link-token-apis",
      "receipt-apis",
      "linked-identity-group-apis",
      "attachment-apis",
      "ui-based-use-cases-api-storage-mapping",
    ],
  },
] as const;

type StageId = (typeof FLOW_STAGES)[number]["id"];

const PHASE_COLORS: Record<string, { bg: string; color: string; label: string }> = {
  ingestion: { bg: "#dbeafe", color: "#1d4ed8", label: "Ingestion" },
  processing: { bg: "#ede9fe", color: "#6d28d9", label: "Processing" },
  storage: { bg: "#d1fae5", color: "#065f46", label: "Storage" },
  caching: { bg: "#fef3c7", color: "#92400e", label: "Caching" },
  query: { bg: "#f1f5f9", color: "#334155", label: "Query" },
  identity: { bg: "#fce7f3", color: "#9d174d", label: "Identity" },
  general: { bg: "#f3f4f6", color: "#374151", label: "General" },
};

function renderInline(text: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  const regex = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
  let lastIndex = 0;
  let match;
  let key = 0;
  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) parts.push(text.slice(lastIndex, match.index));
    const token = match[0];
    if (token.startsWith("**")) {
      parts.push(<strong key={key++}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith("*")) {
      parts.push(<em key={key++}>{token.slice(1, -1)}</em>);
    } else if (token.startsWith("`")) {
      parts.push(<code key={key++} className="cf-inline-code">{token.slice(1, -1)}</code>);
    } else {
      const m = /\[([^\]]+)\]\(([^)]+)\)/.exec(token);
      if (m) parts.push(<a key={key++} href={m[2]} target="_blank" rel="noopener noreferrer" className="cf-link">{m[1]}</a>);
    }
    lastIndex = match.index + token.length;
  }
  if (lastIndex < text.length) parts.push(text.slice(lastIndex));
  return parts.length === 0 ? text : <>{parts}</>;
}

function renderContent(content: string): JSX.Element {
  const lines = content.split("\n");
  const elements: JSX.Element[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (line.trim().startsWith("```")) {
      const lang = line.trim().slice(3);
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      elements.push(
        <pre key={i} className={`cf-code-block cf-code-lang-${lang || "text"}`}>
          <code>{codeLines.join("\n")}</code>
        </pre>
      );
      i++;
      continue;
    }

    if (line.startsWith("|")) {
      const tableRows: string[] = [];
      while (i < lines.length && lines[i].startsWith("|")) {
        if (!/^\|[-:\s|]+\|$/.test(lines[i].trim())) {
          tableRows.push(lines[i]);
        }
        i++;
      }
      if (tableRows.length > 0) {
        elements.push(
          <div key={`table-${i}`} className="cf-table-wrap">
            <table className="cf-table">
              <tbody>
                {tableRows.map((row, ri) => (
                  <tr key={ri} className={ri === 0 ? "cf-table-head" : ""}>
                    {row
                      .split("|")
                      .slice(1, -1)
                      .map((cell, ci) => (
                        <td key={ci}>{renderInline(cell.trim())}</td>
                      ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }
      continue;
    }

    if (line.trim() === "") {
      elements.push(<div key={`sp-${i}`} className="cf-content-spacer" />);
      i++;
      continue;
    }

    if (/^[-*] /.test(line)) {
      elements.push(
        <div key={i} className="cf-bullet-row">
          <span className="cf-bullet-dot">▸</span>
          <span>{renderInline(line.slice(2))}</span>
        </div>
      );
      i++;
      continue;
    }

    const numberedMatch = /^(\d+)\. (.+)/.exec(line);
    if (numberedMatch) {
      elements.push(
        <div key={i} className="cf-numbered-row">
          <span className="cf-numbered-index">{numberedMatch[1]}.</span>
          <span>{renderInline(numberedMatch[2])}</span>
        </div>
      );
      i++;
      continue;
    }

    const headingMatch = /^(#{1,4}) (.+)/.exec(line);
    if (headingMatch) {
      const level = headingMatch[1].length;
      elements.push(
        <p key={i} className={`cf-content-heading cf-heading-${level}`}>
          {renderInline(headingMatch[2])}
        </p>
      );
      i++;
      continue;
    }

    if (line.trim().startsWith("---") || line.trim().startsWith("***")) {
      elements.push(<hr key={i} className="cf-hr" />);
      i++;
      continue;
    }

    elements.push(
      <p key={i} className="cf-content-p">
        {renderInline(line)}
      </p>
    );
    i++;
  }

  return <div className="cf-rendered-content">{elements}</div>;
}

export default function ConsentFlowPanel() {
  const [selectedStage, setSelectedStage] = useState<StageId | null>(null);
  const [expandedSection, setExpandedSection] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [chatHistory, setChatHistory] = useState<
    Array<{ role: "user" | "assistant"; text: string; sections?: Array<{ id: string; title: string }> }>
  >([]);

  const sectionsQuery = useQuery({
    queryKey: ["consent-flow-sections"],
    queryFn: fetchConsentFlowSections,
  });

  const askMutation = useMutation({ mutationFn: askConsentFlow });
  const indexMutation = useMutation({ mutationFn: indexConsentFlow });

  const sections = sectionsQuery.data ?? [];

  const visibleSections = selectedStage
    ? sections.filter((s) => {
        const stage = FLOW_STAGES.find((st) => st.id === selectedStage);
        return stage?.sectionIds.includes(s.id as never) ?? false;
      })
    : sections.filter((s) => s.id !== "complete-consent-flow");

  const handleAsk = async () => {
    const q = question.trim();
    if (!q) return;
    setChatHistory((prev) => [...prev, { role: "user", text: q }]);
    setQuestion("");
    try {
      const result = await askMutation.mutateAsync({ question: q });
      setChatHistory((prev) => [
        ...prev,
        { role: "assistant", text: result.answer, sections: result.sections_used },
      ]);
    } catch {
      setChatHistory((prev) => [
        ...prev,
        { role: "assistant", text: "Unable to get a response right now. Check backend and Azure OpenAI config." },
      ]);
    }
  };

  const handleFollowUp = (q: string) => {
    setQuestion(q);
  };

  const handleSectionAsk = (section: ConsentFlowSection) => {
    const q = `Explain the "${section.title}" part of the consent flow`;
    setQuestion(q);
  };

  return (
    <div className="cf-panel">
      <div className="cf-panel-header">
        <div>
          <h2 className="cf-panel-title">🔄 Consent Flow Explorer</h2>
          <p className="muted">
            Interactive map of the end-to-end OneTrust consent receipt ingestion pipeline.
            Click a stage to explore its components, then ask the AI assistant below.
          </p>
        </div>
        <div className="cf-panel-actions">
          {indexMutation.data ? (
            <span className="cf-index-status">
              ✓ Indexed {indexMutation.data.indexed}/{indexMutation.data.total} sections
            </span>
          ) : null}
          <button
            className="ghost-button"
            type="button"
            onClick={() => indexMutation.mutate()}
            disabled={indexMutation.isPending}
          >
            {indexMutation.isPending ? "Indexing..." : "Index for AI search"}
          </button>
        </div>
      </div>

      {/* Pipeline visualization */}
      <div className="cf-pipeline-wrap">
        <div className="cf-pipeline">
          {FLOW_STAGES.map((stage, idx) => (
            <Fragment key={stage.id}>
              <button
                type="button"
                className={`cf-stage-node ${selectedStage === stage.id ? "cf-stage-node-active" : ""}`}
                style={
                  {
                    "--stage-color": stage.color,
                    "--stage-bg": stage.bg,
                    "--stage-border": stage.border,
                  } as React.CSSProperties
                }
                onClick={() => setSelectedStage(selectedStage === stage.id ? null : stage.id)}
              >
                <span className="cf-stage-icon">{stage.icon}</span>
                <span className="cf-stage-label">{stage.label}</span>
                <span className="cf-stage-desc">{stage.description}</span>
                <span className="cf-stage-sub">{stage.sub}</span>
              </button>
              {idx < FLOW_STAGES.length - 1 && (
                <div className="cf-pipeline-arrow">
                  <svg viewBox="0 0 40 20" className="cf-arrow-svg" aria-hidden="true">
                    <path d="M0 10 L32 10 M26 4 L32 10 L26 16" strokeWidth="2" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
              )}
            </Fragment>
          ))}
        </div>
        {selectedStage && (
          <div className="cf-stage-filter-label">
            Showing sections for:{" "}
            <strong>{FLOW_STAGES.find((s) => s.id === selectedStage)?.label}</strong>
            <button
              type="button"
              className="cf-clear-filter"
              onClick={() => setSelectedStage(null)}
            >
              ✕ Clear
            </button>
          </div>
        )}
      </div>

      {/* Main content grid */}
      <div className="cf-content-grid">
        {/* Left: Section explorer */}
        <div className="cf-sections-col">
          {sectionsQuery.isLoading ? (
            <p className="muted">Loading consent flow sections...</p>
          ) : sectionsQuery.isError ? (
            <p className="error">Failed to load consent flow sections.</p>
          ) : visibleSections.length === 0 ? (
            <p className="muted">No sections found for this stage.</p>
          ) : (
            <div className="cf-sections-list">
              {visibleSections.map((section) => {
                const phaseStyle = PHASE_COLORS[section.phase] ?? PHASE_COLORS.general;
                const isExpanded = expandedSection === section.id;
                return (
                  <article
                    key={section.id}
                    className={`cf-section-card ${isExpanded ? "cf-section-card-expanded" : ""}`}
                  >
                    <div
                      className="cf-section-card-header"
                      role="button"
                      tabIndex={0}
                      onClick={() => setExpandedSection(isExpanded ? null : section.id)}
                      onKeyDown={(e) => e.key === "Enter" && setExpandedSection(isExpanded ? null : section.id)}
                    >
                      <div className="cf-section-card-meta">
                        <span
                          className="cf-phase-tag"
                          style={{ background: phaseStyle.bg, color: phaseStyle.color }}
                        >
                          {phaseStyle.label}
                        </span>
                        <span className="cf-service-tag">{section.service}</span>
                      </div>
                      <div className="cf-section-title-row">
                        <h3 className="cf-section-title">{section.title}</h3>
                        <span className="cf-expand-chevron">{isExpanded ? "▲" : "▼"}</span>
                      </div>
                      {!isExpanded && (
                        <p className="cf-section-excerpt muted">{section.excerpt}</p>
                      )}
                    </div>

                    {isExpanded && (
                      <div className="cf-section-body">
                        {renderContent(section.content)}
                        <div className="cf-section-actions">
                          <button
                            type="button"
                            className="ghost-button cf-ask-section-btn"
                            onClick={() => handleSectionAsk(section)}
                          >
                            🤖 Ask AI about this
                          </button>
                        </div>
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          )}
        </div>

        {/* Right: AI Assistant */}
        <aside className="cf-assistant-col">
          <div className="cf-assistant-panel card-elevated">
            <div className="cf-assistant-header">
              <h3>🤖 Flow Assistant</h3>
              <p className="muted">
                Ask questions about the consent flow architecture, services, Kafka topics, and APIs.
              </p>
            </div>

            <div className="cf-chat-window">
              {chatHistory.length === 0 && (
                <div className="cf-chat-empty">
                  <p className="muted">Try asking:</p>
                  <div className="cf-suggestions">
                    {[
                      "What Kafka topics route bulk imports?",
                      "How does the escape lane work?",
                      "Where is the DataSubject written to Cosmos DB?",
                      "What APIs query ds-preference-cache?",
                    ].map((q) => (
                      <button
                        key={q}
                        type="button"
                        className="cf-suggestion-chip"
                        onClick={() => handleFollowUp(q)}
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {chatHistory.map((msg, idx) => (
                <div
                  key={idx}
                  className={`cf-chat-bubble ${msg.role === "user" ? "cf-bubble-user" : "cf-bubble-assistant"}`}
                >
                  {msg.role === "assistant" ? (
                    <div className="cf-assistant-msg">
                      <div className="cf-assistant-text">
                        {renderContent(msg.text)}
                      </div>
                      {msg.sections && msg.sections.length > 0 && (
                        <div className="cf-sources-row">
                          <span className="cf-sources-label">Sources:</span>
                          {msg.sections.map((src) => (
                            <button
                              key={src.id}
                              type="button"
                              className="cf-source-chip"
                              onClick={() => {
                                setExpandedSection(src.id);
                                const stage = FLOW_STAGES.find((st) =>
                                  st.sectionIds.includes(src.id as never)
                                );
                                if (stage) setSelectedStage(stage.id);
                              }}
                            >
                              📄 {src.title}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : (
                    <span>{msg.text}</span>
                  )}
                </div>
              ))}
              {askMutation.isPending && (
                <div className="cf-chat-bubble cf-bubble-assistant">
                  <div className="typing-indicator">
                    <span />
                    <span />
                    <span />
                  </div>
                </div>
              )}
            </div>

            {/* Follow-up suggestions from last response */}
            {askMutation.data?.follow_up_questions && askMutation.data.follow_up_questions.length > 0 && (
              <div className="cf-followups">
                {askMutation.data.follow_up_questions.map((q) => (
                  <button
                    key={q}
                    type="button"
                    className="cf-followup-chip"
                    onClick={() => handleFollowUp(q)}
                  >
                    ↩ {q}
                  </button>
                ))}
              </div>
            )}

            <div className="cf-chat-form">
              <textarea
                className="cf-chat-input"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask about Kafka topics, services, APIs, data flows..."
                rows={2}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void handleAsk();
                  }
                }}
                disabled={askMutation.isPending}
              />
              <button
                type="button"
                className="primary-toolbar-button cf-send-btn"
                onClick={() => void handleAsk()}
                disabled={askMutation.isPending || !question.trim()}
              >
                {askMutation.isPending ? "..." : "Ask"}
              </button>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
