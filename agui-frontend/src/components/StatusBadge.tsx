import type { RunStatus } from "../types";

interface StatusBadgeProps {
  status: RunStatus;
}

const labels: Record<RunStatus, string> = {
  idle: "idle",
  running: "running",
  done: "done",
  error: "error"
};

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span className={`status-badge status-${status}`} aria-live="polite">
      <span className="status-dot" />
      {labels[status]}
    </span>
  );
}
