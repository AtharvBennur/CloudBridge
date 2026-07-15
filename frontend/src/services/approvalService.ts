import { apiClient } from "./apiClient";

export interface ApprovalCheckResult {
  requires_approval: boolean;
  pending_events: number;
  blocked: boolean;
  message: string;
}

export interface ApprovalSummary {
  total_changes: number;
  pending_approval: number;
  auto_approved: number;
  rejected: number;
  ignored: number;
  by_risk_level: {
    SAFE: number;
    MODERATE: number;
    HIGH: number;
    CRITICAL: number;
  };
}

export interface BulkApproveResult {
  approved_count: number;
  skipped_count: number;
  message: string;
}

export const approvalService = {
  async checkForApproval(migrationId: number): Promise<ApprovalCheckResult> {
    const response = await apiClient.post(`/schema-approval/check/${migrationId}`);
    return response.data;
  },

  async approveAndResume(migrationId: number, eventIds: number[], approvedBy: string): Promise<any> {
    const response = await apiClient.post(`/schema-approval/approve-and-resume/${migrationId}`, {
      event_ids: eventIds,
      approved_by: approvedBy,
    });
    return response.data;
  },

  async autoApplySafe(migrationId: number): Promise<any> {
    const response = await apiClient.post(`/schema-approval/auto-apply/${migrationId}`);
    return response.data;
  },

  async getApprovalSummary(migrationId: number): Promise<ApprovalSummary> {
    const response = await apiClient.get(`/schema-approval/summary/${migrationId}`);
    return response.data;
  },

  async bulkApprove(migrationId: number, maxRiskLevel: string, approvedBy: string): Promise<BulkApproveResult> {
    const response = await apiClient.post(`/schema-approval/bulk-approve/${migrationId}`, {
      max_risk_level: maxRiskLevel,
      approved_by: approvedBy,
    });
    return response.data;
  },
};
