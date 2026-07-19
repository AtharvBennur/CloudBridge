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
  source_database: string;
  destination_database: string;
  status: string;
  description: string | null;
  aws_connection_id: number | null;
  source_database_config_id: number | null;
  destination_database_config_id: number | null;
  progress_percent: number;
  rows_migrated: number;
  total_rows: number | null;
  current_table: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateMigrationPayload {
  job_name: string;
  source_database: string;
  destination_database: string;
  description?: string;
}

export interface UpdateMigrationPayload {
  job_name?: string;
  source_database?: string;
  destination_database?: string;
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

  async start(migrationId: number): Promise<any> {
    const response = await apiClient.post<any>("/migration-engine/start", { migration_id: migrationId });
    return response.data;
  },

  async pause(migrationId: number): Promise<any> {
    const response = await apiClient.post<any>("/migration-engine/pause", { migration_id: migrationId });
    return response.data;
  },

  async resume(migrationId: number): Promise<any> {
    const response = await apiClient.post<any>("/migration-engine/resume", { migration_id: migrationId });
    return response.data;
  },

  async cancel(migrationId: number): Promise<any> {
    const response = await apiClient.post<any>("/migration-engine/cancel", { migration_id: migrationId });
    return response.data;
  },

  async retry(migrationId: number): Promise<any> {
    const response = await apiClient.post<any>("/migration-engine/retry", { migration_id: migrationId });
    return response.data;
  },

  async getStatus(migrationId: number): Promise<any> {
    const response = await apiClient.get<any>(`/migration-engine/${migrationId}/status`);
    return response.data;
  },
};
