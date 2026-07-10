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
  created_at: string;
  updated_at: string;
}

export interface CreateAWSConnectionPayload {
  aws_account_id: string;
  aws_region: string;
  role_arn: string;
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
};
