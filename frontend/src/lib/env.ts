export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:5000",
  cognitoRegion: import.meta.env.VITE_COGNITO_REGION || "",
  cognitoUserPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID || "",
  cognitoClientId: import.meta.env.VITE_COGNITO_CLIENT_ID || "",
};
