import { useEffect, useState } from "react";
import { fetchAgents } from "./api";
import { AgentForm } from "./components/AgentForm";
import { EventStream } from "./components/EventStream";
import { StatusBadge } from "./components/StatusBadge";
import { useAgentRun } from "./hooks/useAgentRun";
import type { AgentRunRequest, RegistryResponse } from "./types";
import "./styles.css";

export default function App() {
  const [registry, setRegistry] = useState<RegistryResponse | null>(null);
  const [registryError, setRegistryError] = useState<string | null>(null);
  const [loadingRegistry, setLoadingRegistry] = useState(true);
  const { events, status, textContent, runAgent } = useAgentRun();

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

  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">AG-UI</p>
          <h1>Agent Runner</h1>
        </div>
        <StatusBadge status={status} />
      </header>

      <AgentForm
        registry={registry}
        loading={loadingRegistry}
        error={registryError}
        status={status}
        onRun={handleRun}
      />

      <EventStream events={events} textContent={textContent} />
    </main>
  );
}
