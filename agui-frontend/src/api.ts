import type { RegistryResponse } from "./types";

export const BASE_URL =
  import.meta.env.VITE_AGUI_BASE_URL ?? "http://localhost:8002";

export async function fetchAgents(): Promise<RegistryResponse> {
  const response = await fetch(`${BASE_URL}/agents`);

  if (!response.ok) {
    throw new Error(`Failed to fetch agents: ${response.status}`);
  }

  return response.json();
}
