import { useEffect, useRef } from "react";
import type { AgUIEvent } from "../types";

interface EventStreamProps {
  events: AgUIEvent[];
  textContent: string;
}

function renderEvent(event: AgUIEvent, index: number) {
  switch (event.type) {
    case "RUN_STARTED":
      return (
        <div className="event-line event-run" key={index}>
          [RUN_STARTED] thread: {event.threadId}, run: {event.runId}
        </div>
      );
    case "RUN_FINISHED":
      return (
        <div className="event-line event-run" key={index}>
          [RUN_FINISHED]
        </div>
      );
    case "RUN_ERROR":
      return (
        <div className="event-line event-error" key={index}>
          [RUN_ERROR] {event.code ? `${event.code}: ` : ""}
          {event.message ?? "Unknown error"}
        </div>
      );
    case "STEP_STARTED":
      return (
        <div className="event-line event-step" key={index}>
          [STEP_STARTED] {event.stepName}
        </div>
      );
    case "STEP_FINISHED":
      return (
        <div className="event-line event-step" key={index}>
          [STEP_FINISHED] {event.stepName}
        </div>
      );
    case "TEXT_MESSAGE_CONTENT":
      return (
        <div className="event-line event-content" key={index}>
          {event.delta}
        </div>
      );
    case "TEXT_MESSAGE_START":
    case "TEXT_MESSAGE_END":
      return null;
    default:
      return null;
  }
}

export function EventStream({ events, textContent }: EventStreamProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [events]);

  return (
    <section className="output-panel" aria-live="polite">
      <div className="output-header">
        <h2>Output</h2>
        <span>{events.length} events</span>
      </div>
      <div className="event-stream">
        {events.length === 0 ? (
          <div className="empty-state">No run started.</div>
        ) : (
          events.map(renderEvent)
        )}
        <div ref={bottomRef} />
      </div>
      <textarea
        className="raw-output"
        value={textContent}
        readOnly
        aria-label="Accumulated text output"
      />
    </section>
  );
}
