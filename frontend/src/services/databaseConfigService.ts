/*
Purpose:
This file contains the Database Configuration API client helpers used by the React frontend.
*/

import { apiClient } from "@/services/apiClient";

export interface DatabaseConfig {
  id: number;
  name: string;
  database_type: string;
  host: string;
  port: number;
  username: string;
  database_name: string | null;
  purpose: string;
  aws_connection_id: number | null;
  secret_arn: string | null;
  secret_name: string | null;
  provisioning_config: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateDatabaseConfigPayload {
  name: string;
  database_type: string;
  host: string;
  port: number;
  username: string;
  password?: string;
  purpose: string;
  database_name?: string;
  aws_connection_id?: number | null;
  secret_arn?: string;
  secret_name?: string;
  provisioning_config?: string;
}

// ── Validation types ─────────────────────────────────────────────────────────

export interface ValidateDatabasePayload {
  database_type: string;
  host: string;
  port: number;
  username: string;
  password: string;
  database_name?: string;
}

export interface ValidationCheck {
  step: string;
  label: string;
  passed: boolean;
  detail?: string;
}

export interface SourceValidationResult {
  connection: string;
  database: string;
  selectedTable: string | null;
  columns: string[];
  sampleRows: Record<string, unknown>[];
  rowCount: number | null;
  tables: string[];
  checks: ValidationCheck[];
  maskedColumns: string[];
}

export interface DestinationValidationResult {
  connection: string;
  databaseExists: boolean;
  writePermission: boolean;
  readPermission: boolean;
  checks: ValidationCheck[];
}

export const databaseConfigService = {
  async list(): Promise<DatabaseConfig[]> {
    const response = await apiClient.get<DatabaseConfig[]>("/database-configs");
    return response.data;
  },

  async getById(id: number): Promise<DatabaseConfig> {
    const response = await apiClient.get<DatabaseConfig>(`/database-configs/${id}`);
    return response.data;
  },

  async create(payload: CreateDatabaseConfigPayload): Promise<DatabaseConfig> {
    const response = await apiClient.post<DatabaseConfig>("/database-configs", payload);
    return response.data;
  },

  async update(id: number, payload: Partial<CreateDatabaseConfigPayload>): Promise<DatabaseConfig> {
    const response = await apiClient.put<DatabaseConfig>(`/database-configs/${id}`, payload);
    return response.data;
  },

  async remove(id: number): Promise<{ message: string }> {
    const response = await apiClient.delete<{ message: string }>(`/database-configs/${id}`);
    return response.data;
  },

  async validateSource(payload: ValidateDatabasePayload): Promise<SourceValidationResult> {
    const response = await apiClient.post<SourceValidationResult>("/database-configs/validate", { ...payload, purpose: "SOURCE" }, { timeout: 30_000 });
    return response.data;
  },

  async validateDestination(payload: ValidateDatabasePayload): Promise<DestinationValidationResult> {
    const response = await apiClient.post<DestinationValidationResult>("/database-configs/validate", { ...payload, purpose: "DESTINATION" }, { timeout: 30_000 });
    return response.data;
  },
};
