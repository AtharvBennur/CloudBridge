import { apiClient } from "./apiClient";

export interface CDCConfig {
  id: number;
  migration_id: number;
  cdc_mode: "FULL_LOAD" | "FULL_LOAD_AND_CDC" | "CDC_ONLY";
  status: "IDLE" | "RUNNING" | "PAUSED" | "STOPPED";
  replication_slot_name?: string;
  wal_level?: string;
  max_lag_seconds?: number;
  checkpoint_interval?: number;
  created_at: string;
  updated_at: string;
}

export interface CDCEvent {
  id: number;
  migration_id: number;
  event_type: "INSERT" | "UPDATE" | "DELETE";
  table_name: string;
  row_data?: Record<string, any>;
  old_data?: Record<string, any>;
  status: "PENDING" | "PROCESSED" | "FAILED";
  error_message?: string;
  processed_at?: string;
  created_at: string;
}

export interface CDCStatistics {
  total_events: number;
  processed_events: number;
  failed_events: number;
  pending_events: number;
  events_per_second: number;
  avg_lag_seconds: number;
  by_event_type: {
    INSERT: number;
    UPDATE: number;
    DELETE: number;
  };
}

export const cdcService = {
  async createConfig(migrationId: number, config: Partial<CDCConfig>): Promise<CDCConfig> {
    const response = await apiClient.post("/cdc/config", {
      migration_id: migrationId,
      ...config,
    });
    return response.data;
  },

  async getConfig(migrationId: number): Promise<CDCConfig> {
    const response = await apiClient.get(`/cdc/config/${migrationId}`);
    return response.data;
  },

  async updateConfig(migrationId: number, config: Partial<CDCConfig>): Promise<CDCConfig> {
    const response = await apiClient.put(`/cdc/config/${migrationId}`, config);
    return response.data;
  },

  async deleteConfig(migrationId: number): Promise<void> {
    await apiClient.delete(`/cdc/config/${migrationId}`);
  },

  async start(migrationId: number): Promise<{ migration_id: number; status: string; message: string }> {
    const response = await apiClient.post("/cdc/start", { migration_id: migrationId });
    return response.data;
  },

  async pause(migrationId: number): Promise<{ migration_id: number; status: string; message: string }> {
    const response = await apiClient.post("/cdc/pause", { migration_id: migrationId });
    return response.data;
  },

  async resume(migrationId: number): Promise<{ migration_id: number; status: string; message: string }> {
    const response = await apiClient.post("/cdc/resume", { migration_id: migrationId });
    return response.data;
  },

  async stop(migrationId: number): Promise<{ migration_id: number; status: string; message: string }> {
    const response = await apiClient.post("/cdc/stop", { migration_id: migrationId });
    return response.data;
  },

  async getEvents(migrationId: number, status?: string, limit: number = 100): Promise<CDCEvent[]> {
    const params: any = { limit };
    if (status) params.status = status;
    const response = await apiClient.get(`/cdc/events/${migrationId}`, { params });
    return response.data;
  },

  async getStatistics(migrationId: number): Promise<CDCStatistics> {
    const response = await apiClient.get(`/cdc/statistics/${migrationId}`);
    return response.data;
  },
};
