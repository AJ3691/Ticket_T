import { useEffect, useState } from "react";
import { fetchAgents } from "./api";
import { AgentForm } from "./components/AgentForm";
import { EventStream } from "./components/EventStream";
import { StatusBadge } from "./components/StatusBadge";
import { TriageForm } from "./components/TriageForm";
import { useAgentRun } from "./hooks/useAgentRun";
import type {
  AgentRunRequest,
  LangGraphTriageRequest,
  RegistryResponse,
  RunMode
} from "./types";
import "./styles.css";

export default function App() {
  const [registry, setRegistry] = useState<RegistryResponse | null>(null);
  const [registryError, setRegistryError] = useState<string | null>(null);
  const [loadingRegistry, setLoadingRegistry] = useState(true);
  const [mode, setMode] = useState<RunMode>("agent");
  const { events, status, textContent, runAgent, runLangGraphTriage, reset } =
    useAgentRun();

  useEffect(() => {
    let cancelled = false;

    async function loadRegistry() {
      try {
        const data = await fetchAgents();
        if (!cancelled) {
          setRegistry(data);
          setRegistryError(null);
        }
      } catch (error) {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : String(error);
          setRegistryError(message);
        }
      } finally {
        if (!cancelled) {
          setLoadingRegistry(false);
        }
      }
    }

    loadRegistry();

    return () => {
      cancelled = true;
    };
  }, []);

  function handleRun(input: AgentRunRequest) {
    runAgent(input);
  }

  function handleTriageRun(input: LangGraphTriageRequest) {
    runLangGraphTriage(input);
  }

  function changeMode(nextMode: RunMode) {
    setMode(nextMode);
    reset();
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">AG-UI</p>
          <h1>Agent Runner</h1>
        </div>
        <StatusBadge status={status} />
      </header>

      <div className="mode-toggle" aria-label="Run mode">
        <button
          type="button"
          className={mode === "agent" ? "active" : ""}
          onClick={() => changeMode("agent")}
          disabled={status === "running"}
        >
          Agent Runner
        </button>
        <button
          type="button"
          className={mode === "langgraph" ? "active" : ""}
          onClick={() => changeMode("langgraph")}
          disabled={status === "running"}
        >
          LangGraph Triage
        </button>
      </div>

      {mode === "agent" ? (
        <AgentForm
          registry={registry}
          loading={loadingRegistry}
          error={registryError}
          status={status}
          onRun={handleRun}
        />
      ) : (
        <TriageForm status={status} onRun={handleTriageRun} />
      )}

      <EventStream events={events} textContent={textContent} />
    </main>
  );
}
