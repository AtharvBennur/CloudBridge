/*
Purpose:
This file contains the migration API client helpers used by the React frontend.

Why:
The application needs a dedicated service layer so components can stay focused on presentation and user interaction.

Architecture:
React Pages
↓
Migration Service
↓
Axios API Client
↓
Flask Backend
*/

import { apiClient } from "@/services/apiClient";

export interface MigrationJob {
  id: number;
  job_name: string;
  source_database_config_id: number | null;
  destination_database_config_id: number | null;
  status: string;
  description: string | null;
  aws_connection_id: number | null;
  progress_percent: number;
  rows_migrated: number;
  total_rows: number | null;
  current_table: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  // Legacy fields for backward compatibility
  source_database?: string;
  destination_database?: string;
}

export interface CreateMigrationPayload {
  job_name: string;
  source_database_config_id: number;
  destination_database_config_id: number;
  description?: string;
}

export interface UpdateMigrationPayload {
  job_name?: string;
  source_database_config_id?: number;
  destination_database_config_id?: number;
  status?: string;
  description?: string;
}

export interface DeleteMigrationResponse {
  message: string;
}

export const migrationService = {
  async list(): Promise<MigrationJob[]> {
    const response = await apiClient.get<MigrationJob[]>("/migrations");
    return response.data;
  },

  async getById(id: number): Promise<MigrationJob> {
    const response = await apiClient.get<MigrationJob>(`/migrations/${id}`);
    return response.data;
  },

  async create(payload: CreateMigrationPayload): Promise<MigrationJob> {
    const response = await apiClient.post<MigrationJob>("/migrations", payload);
    return response.data;
  },

  async update(id: number, payload: UpdateMigrationPayload): Promise<MigrationJob> {
    const response = await apiClient.put<MigrationJob>(`/migrations/${id}`, payload);
    return response.data;
  },

  async remove(id: number): Promise<DeleteMigrationResponse> {
    const response = await apiClient.delete<DeleteMigrationResponse>(`/migrations/${id}`);
    return response.data;
  },

  async start(migrationId: number, awsConnectionId?: number): Promise<any> {
    const response = await apiClient.post<any>("/ecs/start-migration", { 
      migration_id: migrationId,
      aws_connection_id: awsConnectionId
    });
    return response.data;
  },

  async pause(migrationId: number): Promise<any> {
    // First get the ECS task for this migration, then pause it
    const response = await apiClient.get<any>(`/ecs/tasks?migration_id=${migrationId}`);
    const tasks = response.data;
    if (tasks.length === 0) throw new Error("No ECS task found for this migration");
    const taskId = tasks[0].id;
    const pauseResponse = await apiClient.post<any>(`/ecs/tasks/${taskId}/pause`);
    return pauseResponse.data;
  },

  async resume(migrationId: number): Promise<any> {
    // First get the ECS task for this migration, then resume it
    const response = await apiClient.get<any>(`/ecs/tasks?migration_id=${migrationId}`);
    const tasks = response.data;
    if (tasks.length === 0) throw new Error("No ECS task found for this migration");
    const taskId = tasks[0].id;
    const resumeResponse = await apiClient.post<any>(`/ecs/tasks/${taskId}/resume`);
    return resumeResponse.data;
  },

  async cancel(migrationId: number): Promise<any> {
    // First get the ECS task for this migration, then cancel it
    const response = await apiClient.get<any>(`/ecs/tasks?migration_id=${migrationId}`);
    const tasks = response.data;
    if (tasks.length === 0) throw new Error("No ECS task found for this migration");
    const taskId = tasks[0].id;
    const cancelResponse = await apiClient.post<any>(`/ecs/tasks/${taskId}/cancel`);
    return cancelResponse.data;
  },

  async retry(migrationId: number): Promise<any> {
    // First get the ECS task for this migration, then retry it
    const response = await apiClient.get<any>(`/ecs/tasks?migration_id=${migrationId}`);
    const tasks = response.data;
    if (tasks.length === 0) throw new Error("No ECS task found for this migration");
    const taskId = tasks[0].id;
    const retryResponse = await apiClient.post<any>(`/ecs/tasks/${taskId}/retry`);
    return retryResponse.data;
  },

  async getStatus(migrationId: number): Promise<any> {
    // Get ECS task status instead of migration-engine status
    const response = await apiClient.get<any>(`/ecs/tasks?migration_id=${migrationId}`);
    const tasks = response.data;
    if (tasks.length === 0) throw new Error("No ECS task found for this migration");
    const taskId = tasks[0].id;
    const statusResponse = await apiClient.get<any>(`/ecs/tasks/${taskId}/status`);
    return statusResponse.data;
  },
};
