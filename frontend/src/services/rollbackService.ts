import { apiClient } from "./apiClient";

export interface Checkpoint {
  id: number;
  migration_id: number;
  checkpoint_name: string;
  progress_percent: number;
  rows_processed: number;
  checkpoint_metadata?: Record<string, any>;
  created_at: string;
}

export interface RollbackResult {
  success: boolean;
  message: string;
  rows_rolled_back?: number;
  time_taken_seconds?: number;
}

export interface RecoveryOptions {
  can_rollback: boolean;
  can_resume: boolean;
  can_restart: boolean;
  available_checkpoints: number;
  latest_checkpoint?: Checkpoint;
  recommended_action: string;
}

export const rollbackService = {
  async createCheckpoint(data: {
    migration_id: number;
    checkpoint_name?: string;
    metadata?: Record<string, any>;
  }): Promise<Checkpoint> {
    const response = await apiClient.post("/rollback/checkpoint", data);
    return response.data;
  },

  async rollbackToCheckpoint(migrationId: number, checkpointId: number): Promise<RollbackResult> {
    const response = await apiClient.post(`/rollback/to-checkpoint/${migrationId}`, {
      checkpoint_id: checkpointId,
    });
    return response.data;
  },

  async resumeFromCheckpoint(migrationId: number, checkpointId?: number): Promise<RollbackResult> {
    const response = await apiClient.post(`/rollback/resume/${migrationId}`, {
      checkpoint_id: checkpointId,
    });
    return response.data;
  },

  async restartMigration(migrationId: number): Promise<RollbackResult> {
    const response = await apiClient.post(`/rollback/restart/${migrationId}`);
    return response.data;
  },

  async getCheckpoints(migrationId: number): Promise<Checkpoint[]> {
    const response = await apiClient.get(`/rollback/checkpoints/${migrationId}`);
    return response.data;
  },

  async getRecoveryOptions(migrationId: number): Promise<RecoveryOptions> {
    const response = await apiClient.get(`/rollback/recovery-options/${migrationId}`);
    return response.data;
  },

  async deleteCheckpoint(checkpointId: number): Promise<void> {
    await apiClient.delete(`/rollback/checkpoint/${checkpointId}`);
  },

  async cleanupCheckpoints(migrationId: number, keepCount: number = 5): Promise<{ message: string; deleted_count: number }> {
    const response = await apiClient.post(`/rollback/cleanup-checkpoints/${migrationId}`, {
      keep_count: keepCount,
    });
    return response.data;
  },
};
