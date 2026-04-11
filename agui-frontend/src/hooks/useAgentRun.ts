import { useCallback, useState } from "react";
import { BASE_URL } from "../api";
import type { AgentRunRequest, AgUIEvent, RunStatus } from "../types";

function isAgUIEvent(value: unknown): value is AgUIEvent {
  return (
    typeof value === "object" &&
    value !== null &&
    "type" in value &&
    typeof (value as { type: unknown }).type === "string"
  );
}

export function useAgentRun() {
  const [events, setEvents] = useState<AgUIEvent[]>([]);
  const [status, setStatus] = useState<RunStatus>("idle");
  const [textContent, setTextContent] = useState("");

  const reset = useCallback(() => {
    setEvents([]);
    setTextContent("");
    setStatus("idle");
  }, []);

  const runAgent = useCallback(async (request: AgentRunRequest) => {
    setEvents([]);
    setTextContent("");
    setStatus("running");

    try {
      const response = await fetch(`${BASE_URL}/agui`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(request)
      });

      if (!response.ok) {
        throw new Error(`Run request failed: ${response.status}`);
      }

      if (!response.body) {
        throw new Error("Run response did not include a stream body.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";

        for (const part of parts) {
          const lines = part.split("\n");
          for (const line of lines) {
            if (!line.startsWith("data: ")) {
              continue;
            }

            const parsed: unknown = JSON.parse(line.slice(6));
            if (!isAgUIEvent(parsed)) {
              continue;
            }

            setEvents((current) => [...current, parsed]);

            if (parsed.type === "TEXT_MESSAGE_CONTENT") {
              setTextContent((current) => `${current}${parsed.delta}\n`);
            }

            if (parsed.type === "RUN_FINISHED") {
              setStatus("done");
            }

            if (parsed.type === "RUN_ERROR") {
              setStatus("error");
            }
          }
        }
      }

      if (buffer.trim()) {
        const lines = buffer.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const parsed: unknown = JSON.parse(line.slice(6));
            if (isAgUIEvent(parsed)) {
              setEvents((current) => [...current, parsed]);
            }
          }
        }
      }

      setStatus((current) => (current === "running" ? "done" : current));
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setEvents((current) => [
        ...current,
        {
          type: "RUN_ERROR",
          message,
          code: "CLIENT_ERROR"
        }
      ]);
      setStatus("error");
    }
  }, []);

  return { events, status, textContent, runAgent, reset };
}
