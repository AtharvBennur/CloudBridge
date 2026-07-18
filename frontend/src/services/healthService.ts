import { apiClient } from "@/services/apiClient";

export interface HealthResponse {
  status: "healthy" | "degraded";
  database: "connected" | "disconnected";
  timestamp: number;
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await apiClient.get<HealthResponse>("/health");
  return response.data;
}
