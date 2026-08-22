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

export interface PreflightChecks {
  sts: CheckDetail;
  role_access: CheckDetail;
  region: CheckDetail;
  iam_permissions: CheckDetail;
  database_connectivity: CheckDetail;
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
  checks: PreflightChecks;
  database_status: {
    source: { ok: boolean; message: string };
    destination: { ok: boolean; message: string };
  };
}

export interface LambdaReadinessReport {
  status: "READY" | "BLOCKED";
  aws_connection_id: number;
  aws_region: string;
  summary: string;
  functions: {
    orchestrator: { arn: string; status: "READY" | "MISSING" | "REGION_MISMATCH" | "ACCESS_DENIED"; message: string };
    worker: { arn: string; status: "READY" | "MISSING" | "REGION_MISMATCH" | "ACCESS_DENIED"; message: string };
    validation: { arn: string; status: "READY" | "MISSING" | "REGION_MISMATCH" | "ACCESS_DENIED"; message: string };
  };
}

export const preflightService = {
  async run(payload: PreflightPayload): Promise<PreflightReport> {
    const response = await apiClient.post<PreflightReport>("/preflight", payload);
    return response.data;
  },
  async checkLambdaReadiness(payload: { aws_connection_id: number }): Promise<LambdaReadinessReport> {
    const response = await apiClient.post<LambdaReadinessReport>("/preflight/lambda", payload);
    return response.data;
  },
};
