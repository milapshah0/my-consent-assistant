import React, { FormEvent, useState } from "react";

import { useQuery } from "@tanstack/react-query";

import { useChat } from "../hooks/useChat";
import { fetchChatSuggestions } from "../services/api";

type ChatItem = {
  role: "user" | "assistant";
  text: string;
  sources?: Array<{ type: string; title: string; url: string | null }>;
};

type ChatPanelProps = {
  contextTitle?: string;
  contextHint?: string;
  onClose?: () => void;
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
        if (!/^\|[-:\s|]+\|$/.test(lines[i].trim())) tableRows.push(lines[i]);
        i++;
      }
      if (tableRows.length > 0) {
        elements.push(
          <div key={`table-${i}`} className="cf-table-wrap">
            <table className="cf-table">
              <tbody>
                {tableRows.map((row, ri) => (
                  <tr key={ri} className={ri === 0 ? "cf-table-head" : ""}>
                    {row.split("|").slice(1, -1).map((cell, ci) => (
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

    if (/^[-*•] /.test(line)) {
      elements.push(
        <div key={i} className="cf-bullet-row">
          <span className="cf-bullet-dot">▸</span>
          <span>{renderInline(line.replace(/^[-*•] /, ""))}</span>
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

    if (line.trim().startsWith("---")) {
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

export default function ChatPanel({ contextTitle, contextHint, onClose }: ChatPanelProps) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatItem[]>([]);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const chatMutation = useChat();

  const suggestionsQuery = useQuery({
    queryKey: ["chat-suggestions"],
    queryFn: () => fetchChatSuggestions(5),
    staleTime: 5 * 60 * 1000,
  });
  const suggestions = suggestionsQuery.data ?? [];

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!input.trim()) {
      return;
    }

    const userMessage = input.trim();
    setMessages((prev) => [...prev, { role: "user", text: userMessage }]);
    setInput("");

    try {
      const response = await chatMutation.mutateAsync({
        message: userMessage,
        sessionId,
        context:
          contextTitle || contextHint
            ? {
                title: contextTitle,
                hint: contextHint,
              }
            : undefined,
      });
      if (response.session_id) {
        setSessionId(response.session_id);
      }
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: response.answer,
          sources: response.sources,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: "Unable to fetch response right now. Check backend and API credentials.",
        },
      ]);
    }
  };

  const handleFollowUpClick = (question: string) => {
    setInput(question);
  };

  return (
    <article className="chat-card">
      <div className="chat-card-header">
        <div>
          <h2>🤖 Consent Engineering Assistant</h2>
          <p className="muted">Ask questions about consent implementation, technical docs, and architecture.</p>
          {contextTitle ? (
            <div className="chat-context-block">
              <strong>{contextTitle}</strong>
              {contextHint ? <span className="muted">{contextHint}</span> : null}
            </div>
          ) : null}
        </div>
        <div className="chat-header-actions">
          <span className="chat-status-pill">Context aware</span>
          {onClose ? (
            <button type="button" className="chat-close-button" onClick={onClose} aria-label="Close assistant">
              ×
            </button>
          ) : null}
        </div>
      </div>

      <div className="chat-window">
        {messages.length === 0 ? (
          <div className="chat-empty-state">
            <strong>👋 Hi! I'm your consent engineering assistant</strong>
            <p className="muted">Ask me about:</p>
            <div className="chat-suggestions">
              {suggestions.length > 0
                ? suggestions.map((q) => (
                    <button
                      key={q}
                      type="button"
                      className="chat-suggestion-chip"
                      onClick={() => setInput(q)}
                    >
                      {q}
                    </button>
                  ))
                : ["How does the consent receipt pipeline work?", "What Cosmos DB containers store consent data?", "Explain Linked Identity Groups"].map((q) => (
                    <button
                      key={q}
                      type="button"
                      className="chat-suggestion-chip"
                      onClick={() => setInput(q)}
                    >
                      {q}
                    </button>
                  ))}
            </div>
          </div>
        ) : null}
        {messages.map((message, index) => (
          <div key={`${message.role}-${index}`} className={`chat-bubble ${message.role}`}>
            {message.role === "assistant" ? (
              <div className="assistant-message">
                <div className="message-content">
                  {renderContent(message.text)}
                </div>
                {message.sources && message.sources.length > 0 ? (
                  <div className="chat-sources">
                    <strong>📚 Sources</strong>
                    <div className="chat-source-list">
                      {message.sources
                        .filter((source) => source.title)
                        .map((source, sourceIndex) => (
                          <a
                            key={`${source.title}-${sourceIndex}`}
                            className="chat-source-link"
                            href={source.url ?? "#"}
                            target={source.url ? "_blank" : undefined}
                            rel={source.url ? "noreferrer" : undefined}
                          >
                            📄 {source.title}
                          </a>
                        ))}
                    </div>
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="user-message">
                {message.text}
              </div>
            )}
          </div>
        ))}
        {chatMutation.isPending && (
          <div className="chat-bubble assistant">
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}
      </div>

      <form className="chat-form" onSubmit={handleSubmit}>
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Ask about consent implementation, technical docs, or architecture..."
          disabled={chatMutation.isPending}
        />
        <button type="submit" disabled={chatMutation.isPending || !input.trim()}>
          {chatMutation.isPending ? "🤔" : "🚀"}
        </button>
      </form>
    </article>
  );
}
