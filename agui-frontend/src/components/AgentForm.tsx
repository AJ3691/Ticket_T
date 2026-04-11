import type { FormEvent } from "react";
import type { RegistryResponse, RunStatus } from "../types";

interface AgentFormProps {
  registry: RegistryResponse | null;
  loading: boolean;
  error: string | null;
  status: RunStatus;
  onRun: (input: {
    agent: string;
    task: string;
    instruction: string;
    threadId: string;
    runId: string;
  }) => void;
}

function makeId(prefix: string) {
  const random =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : Math.random().toString(16).slice(2);

  return `${prefix}-${random}`;
}

export function AgentForm({
  registry,
  loading,
  error,
  status,
  onRun
}: AgentFormProps) {
  const agents = registry ? Object.keys(registry.agents).sort() : [];
  const tasks = registry ? Object.keys(registry.tasks).sort() : [];
  const isRunning = status === "running";

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const agent = String(form.get("agent") || "");
    const task = String(form.get("task") || "");
    const instruction = String(form.get("instruction") || "").trim();

    if (!agent || !task || !instruction) {
      return;
    }

    onRun({
      agent,
      task,
      instruction,
      threadId: makeId("thread"),
      runId: makeId("run")
    });
  }

  return (
    <form className="agent-form" onSubmit={handleSubmit}>
      <div className="form-grid">
        <label>
          <span>Agent</span>
          <select name="agent" disabled={loading || isRunning || agents.length === 0}>
            {agents.map((agent) => (
              <option key={agent} value={agent}>
                {agent}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span>Task</span>
          <select name="task" disabled={loading || isRunning || tasks.length === 0}>
            {tasks.map((task) => (
              <option key={task} value={task}>
                {task}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label>
        <span>Instruction</span>
        <input
          name="instruction"
          type="text"
          placeholder="Add networking category"
          disabled={loading || isRunning}
        />
      </label>

      <div className="form-actions">
        <button
          type="submit"
          disabled={loading || isRunning || agents.length === 0 || tasks.length === 0}
        >
          Run Agent
        </button>
        {loading && <span className="form-note">Loading registry...</span>}
        {error && <span className="form-error">{error}</span>}
      </div>
    </form>
  );
}
