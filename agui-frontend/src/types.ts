export type EventType =
  | "RUN_STARTED"
  | "RUN_FINISHED"
  | "RUN_ERROR"
  | "STEP_STARTED"
  | "STEP_FINISHED"
  | "TEXT_MESSAGE_START"
  | "TEXT_MESSAGE_CONTENT"
  | "TEXT_MESSAGE_END";

export type RunStatus = "idle" | "running" | "done" | "error";

export interface BaseEvent {
  type: EventType;
  timestamp?: number;
}

export interface RunStartedEvent extends BaseEvent {
  type: "RUN_STARTED";
  threadId: string;
  runId: string;
}

export interface RunFinishedEvent extends BaseEvent {
  type: "RUN_FINISHED";
  threadId: string;
  runId: string;
}

export interface RunErrorEvent extends BaseEvent {
  type: "RUN_ERROR";
  message?: string;
  code?: string;
}

export interface StepStartedEvent extends BaseEvent {
  type: "STEP_STARTED";
  stepName: string;
}

export interface StepFinishedEvent extends BaseEvent {
  type: "STEP_FINISHED";
  stepName: string;
}

export interface TextMessageStartEvent extends BaseEvent {
  type: "TEXT_MESSAGE_START";
  messageId: string;
  role: "assistant" | "user" | "system";
}

export interface TextMessageContentEvent extends BaseEvent {
  type: "TEXT_MESSAGE_CONTENT";
  messageId: string;
  delta: string;
}

export interface TextMessageEndEvent extends BaseEvent {
  type: "TEXT_MESSAGE_END";
  messageId: string;
}

export type AgUIEvent =
  | RunStartedEvent
  | RunFinishedEvent
  | RunErrorEvent
  | StepStartedEvent
  | StepFinishedEvent
  | TextMessageStartEvent
  | TextMessageContentEvent
  | TextMessageEndEvent;

export interface RegistryResponse {
  agents: Record<string, string>;
  tasks: Record<string, string>;
}

export interface AgentRunRequest {
  agent: string;
  task: string;
  instruction: string;
  threadId: string;
  runId: string;
}
