/*
Purpose:
This file contains the AWS connection API client helpers used by the React frontend.

Why:
The application needs a dedicated service layer so components can stay focused on presentation and user interaction.

Architecture:
React Pages
↓
AWS Connection Service
↓
Axios API Client
↓
Flask Backend
*/

import { apiClient } from "@/services/apiClient";

export interface AWSConnection {
  id: number;
  aws_account_id: string;
  aws_region: string;
  role_arn: string;
  external_id: string;
  connection_status: string;
  last_validated_at: string;
  created_at: string;
  updated_at: string;
}

export interface CreateAWSConnectionPayload {
  aws_account_id: string;
  aws_region: string;
  role_arn?: string;
}

export interface UpdateAWSConnectionPayload {
  aws_account_id?: string;
  aws_region?: string;
  role_arn?: string;
  connection_status?: string;
}

export interface DeleteAWSConnectionResponse {
  message: string;
}

export interface STSConnectResult {
  status: string;
  message: string;
  step: string;
  aws_connection_id: number;
  session_assumed: boolean;
  details: {
    session_assumed: boolean;
    assume_role: boolean;
    account_verified: boolean;
    region_accessible: boolean;
    permissions: Record<string, boolean>;
    caller_identity: { arn: string; account: string };
    credentials_expires_at: string;
  };
}

export interface ValidateResult {
  status: string;
  message: string;
  step: string;
  aws_connection_id: number;
  permissions: Record<string, boolean>;
}

export const awsConnectionService = {
  async list(): Promise<AWSConnection[]> {
    const response = await apiClient.get<AWSConnection[]>("/aws-connections");
    return response.data;
  },

  async getById(id: number): Promise<AWSConnection> {
    const response = await apiClient.get<AWSConnection>(`/aws-connections/${id}`);
    return response.data;
  },

  async create(payload: CreateAWSConnectionPayload): Promise<AWSConnection> {
    const response = await apiClient.post<AWSConnection>("/aws-connections", payload);
    return response.data;
  },

  async update(id: number, payload: UpdateAWSConnectionPayload): Promise<AWSConnection> {
    const response = await apiClient.put<AWSConnection>(`/aws-connections/${id}`, payload);
    return response.data;
  },

  async remove(id: number): Promise<DeleteAWSConnectionResponse> {
    const response = await apiClient.delete<DeleteAWSConnectionResponse>(`/aws-connections/${id}`);
    return response.data;
  },

  async connect(id: number): Promise<STSConnectResult> {
    const response = await apiClient.post<STSConnectResult>(`/aws-connections/${id}/connect`);
    return response.data;
  },

  async validate(id: number): Promise<ValidateResult> {
    const response = await apiClient.post<ValidateResult>(`/aws-connections/${id}/validate`);
    return response.data;
  },

  async disconnect(id: number): Promise<any> {
    const response = await apiClient.post<any>(`/aws-connections/${id}/disconnect`);
    return response.data;
  },

  async registerRoleArn(id: number, roleArn: string): Promise<AWSConnection> {
    const response = await apiClient.post<AWSConnection>(`/aws-connections/${id}/register-role-arn`, {
      role_arn: roleArn,
    });
    return response.data;
  },

  async getCloudformationTemplate(id: number): Promise<any> {
    const response = await apiClient.get<any>(`/aws-connections/${id}/cloudformation-template`);
    return response.data;
  },
};
