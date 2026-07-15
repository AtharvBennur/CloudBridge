import { apiClient } from "./apiClient";

export interface AuditLog {
  id: number;
  event_type: string;
  event_category: string;
  event_description: string;
  migration_id?: number;
  aws_connection_id?: number;
  database_config_id?: number;
  ecs_task_id?: number;
  user_id?: string;
  user_email?: string;
  severity: "INFO" | "WARNING" | "ERROR" | "CRITICAL";
  event_metadata?: Record<string, any>;
  occurred_at: string;
  ip_address?: string;
}

export interface MigrationMetrics {
  migration_id: number;
  total_rows: number;
  rows_processed: number;
  rows_remaining: number;
  progress_percent: number;
  avg_rows_per_second: number;
  estimated_time_remaining_seconds: number;
  errors_count: number;
  warnings_count: number;
  checkpoints_created: number;
  last_checkpoint_at?: string;
}

export interface SystemMetrics {
  total_migrations: number;
  running_migrations: number;
  completed_migrations: number;
  failed_migrations: number;
  total_aws_connections: number;
  total_database_configs: number;
  active_ecs_tasks: number;
  total_audit_logs: number;
  avg_migration_duration_seconds: number;
}

export const observabilityService = {
  async createAuditLog(data: Partial<AuditLog>): Promise<AuditLog> {
    const response = await apiClient.post("/observability/audit-log", data);
    return response.data;
  },

  async getAuditLogs(params?: {
    event_type?: string;
    event_category?: string;
    migration_id?: number;
    severity?: string;
    limit?: number;
    offset?: number;
  }): Promise<AuditLog[]> {
    const response = await apiClient.get("/observability/audit-logs", { params });
    return response.data;
  },

  async getMigrationMetrics(migrationId: number): Promise<MigrationMetrics> {
    const response = await apiClient.get(`/observability/metrics/migration/${migrationId}`);
    return response.data;
  },

  async getSystemMetrics(): Promise<SystemMetrics> {
    const response = await apiClient.get("/observability/metrics/system");
    return response.data;
  },

  async sendCloudWatchMetric(data: {
    aws_connection_id: number;
    metric_name: string;
    metric_value: number;
    metric_namespace?: string;
    dimensions?: Record<string, string>;
    unit?: string;
  }): Promise<void> {
    await apiClient.post("/observability/cloudwatch/metric", data);
  },

  async sendCloudWatchLog(data: {
    aws_connection_id: number;
    log_group_name: string;
    log_stream_name: string;
    message: string;
    log_level?: string;
  }): Promise<void> {
    await apiClient.post("/observability/cloudwatch/log", data);
  },
};
