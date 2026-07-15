import { apiClient } from "./apiClient";

export interface ECSTask {
  id: number;
  migration_id: number;
  aws_connection_id: number;
  task_arn?: string;
  cluster_arn: string;
  task_definition_arn: string;
  launch_type: "FARGATE" | "EC2";
  subnet_ids: string[];
  security_group_ids: string[];
  cpu: string;
  memory: string;
  status: "PENDING" | "RUNNING" | "STOPPED" | "FAILED";
  exit_code?: number;
  reason?: string;
  started_at?: string;
  stopped_at?: string;
  created_at: string;
  updated_at: string;
}

export interface ECSTaskStatus {
  task_id: number;
  status: string;
  last_status: string;
  desired_status: string;
  cpu?: string;
  memory?: string;
  stopped_reason?: string;
}

export const ecsService = {
  async createTask(data: {
    migration_id: number;
    aws_connection_id: number;
    cluster_arn: string;
    task_definition_arn: string;
    launch_type: "FARGATE" | "EC2";
    subnet_ids: string[];
    security_group_ids: string[];
    cpu: string;
    memory: string;
  }): Promise<ECSTask> {
    const response = await apiClient.post("/ecs/tasks", data);
    return response.data;
  },

  async startTask(taskId: number): Promise<ECSTask> {
    const response = await apiClient.post(`/ecs/tasks/${taskId}/start`);
    return response.data;
  },

  async stopTask(taskId: number, reason?: string): Promise<ECSTask> {
    const response = await apiClient.post(`/ecs/tasks/${taskId}/stop`, { reason });
    return response.data;
  },

  async getTaskStatus(taskId: number): Promise<ECSTaskStatus> {
    const response = await apiClient.get(`/ecs/tasks/${taskId}/status`);
    return response.data;
  },

  async getTaskLogs(taskId: number, tailLines: number = 100): Promise<{ logs: string[] }> {
    const response = await apiClient.get(`/ecs/tasks/${taskId}/logs`, {
      params: { tail_lines: tailLines },
    });
    return response.data;
  },

  async retryTask(taskId: number): Promise<ECSTask> {
    const response = await apiClient.post(`/ecs/tasks/${taskId}/retry`);
    return response.data;
  },

  async deleteTask(taskId: number): Promise<void> {
    await apiClient.delete(`/ecs/tasks/${taskId}`);
  },

  async listTasks(migrationId: number): Promise<ECSTask[]> {
    const response = await apiClient.get("/ecs/tasks", {
      params: { migration_id: migrationId },
    });
    return response.data;
  },

  async getTask(taskId: number): Promise<ECSTask> {
    const response = await apiClient.get(`/ecs/tasks/${taskId}`);
    return response.data;
  },
};
