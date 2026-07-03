import { apiClient } from "@/services/apiClient";

export interface HealthResponse {
  status: "healthy";
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await apiClient.get<HealthResponse>("/health");
  return response.data;
}
