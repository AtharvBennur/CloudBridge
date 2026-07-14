/*
Purpose:
This file contains the Preflight API client helpers used by the React frontend.
*/

import { apiClient } from "@/services/apiClient";

export interface PreflightPayload {
  aws_connection_id: number;
  source_db_id?: number | null;
  destination_db_id?: number | null;
  database_config_id?: number | null;
}

export interface CheckDetail {
  status: "PASS" | "FAIL";
  message: string;
  details?: any;
}

export interface PreflightReport {
  status: "READY" | "FAILED";
  summary: string;
  timestamp: string;
  aws_connection: {
    id: number;
    account_id: string;
    region: string;
    status: string;
  };
  checks: {
    sts_assume_role: CheckDetail;
    role_access: CheckDetail;
    region: CheckDetail;
    iam_permissions: CheckDetail;
    secrets: CheckDetail;
    database_connectivity: CheckDetail;
  };
  database_status: {
    source: { ok: boolean; message: string };
    destination: { ok: boolean; message: string };
  };
}

export const preflightService = {
  async run(payload: PreflightPayload): Promise<PreflightReport> {
    const response = await apiClient.post<PreflightReport>("/preflight", payload);
    return response.data;
  },
};
