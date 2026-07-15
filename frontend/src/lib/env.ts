export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:5000",
  wsBaseUrl: import.meta.env.VITE_WS_BASE_URL || import.meta.env.VITE_API_BASE_URL?.replace("http", "ws") || "ws://127.0.0.1:5000",
  appName: import.meta.env.VITE_APP_NAME || "CloudBridge",
  appVersion: import.meta.env.VITE_APP_VERSION || "1.0.0",
  debug: import.meta.env.VITE_DEBUG === "true",
  cognitoRegion: import.meta.env.VITE_COGNITO_REGION || "",
  cognitoUserPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID || "",
  cognitoClientId: import.meta.env.VITE_COGNITO_CLIENT_ID || "",
  cognitoIdentityPoolId: import.meta.env.VITE_COGNITO_IDENTITY_POOL_ID || "",
  features: {
    cdc: import.meta.env.VITE_FEATURE_CDC !== "false",
    schemaDrift: import.meta.env.VITE_FEATURE_SCHEMA_DRIFT !== "false",
    approvals: import.meta.env.VITE_FEATURE_APPROVALS !== "false",
    ecs: import.meta.env.VITE_FEATURE_ECS !== "false",
    observability: import.meta.env.VITE_FEATURE_OBSERVABILITY !== "false",
    notifications: import.meta.env.VITE_FEATURE_NOTIFICATIONS !== "false",
    rollback: import.meta.env.VITE_FEATURE_ROLLBACK !== "false",
  },
  ui: {
    defaultTheme: import.meta.env.VITE_DEFAULT_THEME || "system",
    enableAnimations: import.meta.env.VITE_ENABLE_ANIMATIONS !== "false",
  },
};
