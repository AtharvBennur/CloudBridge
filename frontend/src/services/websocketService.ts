import { io, Socket } from "socket.io-client";

export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
}

class WebSocketService {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  connect(url: string): Promise<Socket> {
    return new Promise((resolve, reject) => {
      this.socket = io(url, {
        transports: ["websocket", "polling"],
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionAttempts: this.maxReconnectAttempts,
      });

      this.socket.on("connect", () => {
        console.log("WebSocket connected");
        this.reconnectAttempts = 0;
        resolve(this.socket!);
      });

      this.socket.on("connect_error", (error: any) => {
        console.error("WebSocket connection error:", error);
        this.reconnectAttempts++;
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          reject(error);
        }
      });

      this.socket.on("disconnect", (reason: any) => {
        console.log("WebSocket disconnected:", reason);
      });
    });
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  joinMigration(migrationId: number): void {
    if (this.socket) {
      this.socket.emit("join_migration", { migration_id: migrationId });
    }
  }

  leaveMigration(migrationId: number): void {
    if (this.socket) {
      this.socket.emit("leave_migration", { migration_id: migrationId });
    }
  }

  joinECSTask(taskId: number): void {
    if (this.socket) {
      this.socket.emit("join_ecs_task", { task_id: taskId });
    }
  }

  leaveECSTask(taskId: number): void {
    if (this.socket) {
      this.socket.emit("leave_ecs_task", { task_id: taskId });
    }
  }

  onMigrationProgress(callback: (data: any) => void): void {
    if (this.socket) {
      this.socket.on("migration_progress", callback);
    }
  }

  onMigrationStatusChange(callback: (data: any) => void): void {
    if (this.socket) {
      this.socket.on("migration_status_change", callback);
    }
  }

  onWorkerStatus(callback: (data: any) => void): void {
    if (this.socket) {
      this.socket.on("worker_status", callback);
    }
  }

  onReplicationLag(callback: (data: any) => void): void {
    if (this.socket) {
      this.socket.on("replication_lag", callback);
    }
  }

  onSchemaDriftDetected(callback: (data: any) => void): void {
    if (this.socket) {
      this.socket.on("schema_drift_detected", callback);
    }
  }

  onApprovalRequired(callback: (data: any) => void): void {
    if (this.socket) {
      this.socket.on("approval_required", callback);
    }
  }

  onECSTaskStatus(callback: (data: any) => void): void {
    if (this.socket) {
      this.socket.on("ecs_task_status", callback);
    }
  }

  onError(callback: (data: any) => void): void {
    if (this.socket) {
      this.socket.on("error", callback);
    }
  }

  onMessage(callback: (message: WebSocketMessage) => void): void {
    if (this.socket) {
      this.socket.on("message", callback);
    }
  }

  ping(): void {
    if (this.socket) {
      this.socket.emit("ping");
    }
  }

  isConnected(): boolean {
    return this.socket?.connected || false;
  }
}

export const websocketService = new WebSocketService();
