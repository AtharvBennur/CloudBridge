import { apiClient } from "./apiClient";

export interface NotificationConfig {
  id: number;
  user_id: string;
  notification_type: "EMAIL" | "SLACK" | "WEBHOOK";
  email_address?: string;
  slack_webhook_url?: string;
  slack_channel?: string;
  webhook_url?: string;
  webhook_headers?: Record<string, string>;
  subscribed_events: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Notification {
  id: number;
  config_id: number;
  user_id: string;
  event_type: string;
  subject: string;
  body: string;
  migration_id?: number;
  payload?: Record<string, any>;
  status: "PENDING" | "SENT" | "FAILED";
  error_message?: string;
  sent_at?: string;
  created_at: string;
}

export const notificationService = {
  async createConfig(data: {
    user_id: string;
    notification_type: "EMAIL" | "SLACK" | "WEBHOOK";
    email_address?: string;
    slack_webhook_url?: string;
    slack_channel?: string;
    webhook_url?: string;
    webhook_headers?: Record<string, string>;
    subscribed_events: string[];
  }): Promise<NotificationConfig> {
    const response = await apiClient.post("/notifications/config", data);
    return response.data;
  },

  async getConfig(configId: number): Promise<NotificationConfig> {
    const response = await apiClient.get(`/notifications/config/${configId}`);
    return response.data;
  },

  async getUserConfigs(userId: string): Promise<NotificationConfig[]> {
    const response = await apiClient.get(`/notifications/config/user/${userId}`);
    return response.data;
  },

  async deleteConfig(configId: number): Promise<void> {
    await apiClient.delete(`/notifications/config/${configId}`);
  },

  async sendNotification(data: {
    event_type: string;
    subject: string;
    body: string;
    migration_id?: number;
    payload?: Record<string, any>;
  }): Promise<{ message: string; count: number; notifications: Notification[] }> {
    const response = await apiClient.post("/notifications/send", data);
    return response.data;
  },

  async retryFailed(): Promise<{ message: string }> {
    const response = await apiClient.post("/notifications/retry-failed");
    return response.data;
  },

  async getHistory(params?: {
    user_id?: string;
    event_type?: string;
    migration_id?: number;
    limit?: number;
  }): Promise<Notification[]> {
    const response = await apiClient.get("/notifications/history", { params });
    return response.data;
  },

  async getNotification(notificationId: number): Promise<Notification> {
    const response = await apiClient.get(`/notifications/history/${notificationId}`);
    return response.data;
  },
};
