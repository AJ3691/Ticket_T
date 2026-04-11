import type { FormEvent } from "react";
import type { RunStatus } from "../types";

interface TriageFormProps {
  status: RunStatus;
  onRun: (input: {
    title: string;
    description: string;
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

export function TriageForm({ status, onRun }: TriageFormProps) {
  const isRunning = status === "running";

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const title = String(form.get("title") || "").trim();
    const description = String(form.get("description") || "").trim();

    if (!title || !description) {
      return;
    }

    onRun({
      title,
      description,
      threadId: makeId("thread"),
      runId: makeId("run")
    });
  }

  return (
    <form className="agent-form" onSubmit={handleSubmit}>
      <label>
        <span>Title</span>
        <input
          name="title"
          type="text"
          placeholder="Cannot log in"
          disabled={isRunning}
        />
      </label>

      <label>
        <span>Description</span>
        <textarea
          name="description"
          placeholder="Password reset token expired"
          disabled={isRunning}
          rows={5}
        />
      </label>

      <div className="form-actions">
        <button type="submit" disabled={isRunning}>
          Run LangGraph Triage
        </button>
      </div>
    </form>
  );
}
