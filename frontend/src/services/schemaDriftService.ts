import { apiClient } from "./apiClient";

export interface SchemaSnapshot {
  id: number;
  migration_id: number;
  database_config_id: number;
  snapshot_name: string;
  source_type: "SOURCE" | "TARGET";
  schema_data: Record<string, any>;
  captured_at: string;
}

export interface SchemaDriftEvent {
  id: number;
  migration_id: number;
  snapshot_before_id?: number;
  snapshot_after_id?: number;
  change_type: "CREATE_TABLE" | "ALTER_TABLE" | "DROP_TABLE" | "ADD_COLUMN" | "DROP_COLUMN" | "RENAME_COLUMN" | "CREATE_INDEX" | "DROP_INDEX";
  table_name: string;
  column_name?: string;
  index_name?: string;
  risk_level: "SAFE" | "MODERATE" | "HIGH" | "CRITICAL";
  status: "PENDING" | "APPROVED" | "REJECTED" | "IGNORED" | "AUTO_APPLIED";
  approval_reason?: string;
  rejection_reason?: string;
  approved_by?: string;
  rejected_by?: string;
  detected_at: string;
  reviewed_at?: string;
}

export const schemaDriftService = {
  async createSnapshot(data: {
    migration_id: number;
    database_config_id: number;
    snapshot_name: string;
    source_type: "SOURCE" | "TARGET";
  }): Promise<SchemaSnapshot> {
    const response = await apiClient.post("/schema-drift/snapshots", data);
    return response.data;
  },

  async getSnapshot(snapshotId: number): Promise<SchemaSnapshot> {
    const response = await apiClient.get(`/schema-drift/snapshots/${snapshotId}`);
    return response.data;
  },

  async listSnapshots(migrationId: number): Promise<SchemaSnapshot[]> {
    const response = await apiClient.get("/schema-drift/snapshots", {
      params: { migration_id: migrationId },
    });
    return response.data;
  },

  async compareSchemas(data: {
    migration_id: number;
    snapshot_before_id: number;
    snapshot_after_id: number;
  }): Promise<SchemaDriftEvent[]> {
    const response = await apiClient.post("/schema-drift/compare", data);
    return response.data;
  },

  async listDriftEvents(migrationId: number, status?: string): Promise<SchemaDriftEvent[]> {
    const params: any = {};
    if (status) params.status = status;
    const response = await apiClient.get("/schema-drift/drift-events", {
      params: { migration_id: migrationId, ...params },
    });
    return response.data;
  },

  async getDriftEvent(eventId: number): Promise<SchemaDriftEvent> {
    const response = await apiClient.get(`/schema-drift/drift-events/${eventId}`);
    return response.data;
  },

  async approveDriftEvent(eventId: number, approvedBy: string): Promise<SchemaDriftEvent> {
    const response = await apiClient.post(`/schema-drift/drift-events/${eventId}/approve`, {
      approved_by: approvedBy,
    });
    return response.data;
  },

  async rejectDriftEvent(eventId: number, rejectionReason: string, rejectedBy: string): Promise<SchemaDriftEvent> {
    const response = await apiClient.post(`/schema-drift/drift-events/${eventId}/reject`, {
      rejection_reason: rejectionReason,
      rejected_by: rejectedBy,
    });
    return response.data;
  },

  async ignoreDriftEvent(eventId: number): Promise<SchemaDriftEvent> {
    const response = await apiClient.post(`/schema-drift/drift-events/${eventId}/ignore`);
    return response.data;
  },
};
