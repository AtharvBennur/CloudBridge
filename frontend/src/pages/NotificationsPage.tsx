import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Bell,
  Mail,
  MessageSquare,
  Webhook,
  Plus,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock,
  Search,
  Filter,
  X,
  Loader2,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/context/AuthContext";
import { notificationService } from "@/services/notificationService";

const EVENT_TYPES = [
  "MIGRATION_STARTED",
  "MIGRATION_COMPLETED",
  "MIGRATION_FAILED",
  "MIGRATION_PAUSED",
  "MIGRATION_RESUMED",
  "SCHEMA_DRIFT_DETECTED",
  "APPROVAL_REQUESTED",
  "APPROVAL_GRANTED",
  "CHECKPOINT_CREATED",
];

export function NotificationsPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const [showAddChannel, setShowAddChannel] = useState(false);
  const [channelType, setChannelType] = useState<"EMAIL" | "SLACK" | "WEBHOOK">("EMAIL");
  const [emailAddress, setEmailAddress] = useState("");
  const [slackWebhookUrl, setSlackWebhookUrl] = useState("");
  const [slackChannel, setSlackChannel] = useState("");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [filterEventType, setFilterEventType] = useState<string>("");

  const notificationHistoryQuery = useQuery({
    queryKey: ["notification-history"],
    queryFn: () => notificationService.getHistory({ limit: 50 }),
  });

  const userConfigsQuery = useQuery({
    queryKey: ["notification-configs"],
    queryFn: () =>
      user?.email
        ? notificationService.getUserConfigs(user.email)
        : Promise.resolve([]),
    enabled: !!user?.email,
  });

  const createConfigMutation = useMutation({
    mutationFn: notificationService.createConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notification-configs"] });
      setShowAddChannel(false);
      resetForm();
    },
  });

  const handleRetryFailed = async () => {
    try {
      await notificationService.retryFailed();
      notificationHistoryQuery.refetch();
    } catch (error) {
      console.error("Failed to retry notifications:", error);
    }
  };

  const handleCreateChannel = () => {
    if (!user?.email) return;

    const base = {
      user_id: user.email,
      notification_type: channelType,
      subscribed_events: EVENT_TYPES,
    };

    if (channelType === "EMAIL") {
      createConfigMutation.mutate({ ...base, email_address: emailAddress });
    } else if (channelType === "SLACK") {
      createConfigMutation.mutate({
        ...base,
        slack_webhook_url: slackWebhookUrl,
        slack_channel: slackChannel,
      });
    } else {
      createConfigMutation.mutate({ ...base, webhook_url: webhookUrl });
    }
  };

  const resetForm = () => {
    setEmailAddress("");
    setSlackWebhookUrl("");
    setSlackChannel("");
    setWebhookUrl("");
    setChannelType("EMAIL");
  };

  const notifications = notificationHistoryQuery.data || [];

  const filteredNotifications = notifications.filter((n) => {
    const matchesSearch =
      !searchTerm ||
      n.subject.toLowerCase().includes(searchTerm.toLowerCase()) ||
      n.event_type.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesEvent = !filterEventType || n.event_type === filterEventType;
    return matchesSearch && matchesEvent;
  });

  const sentNotifications = notifications.filter(
    (n) => n.status === "SENT"
  ).length;
  const pendingNotifications = notifications.filter(
    (n) => n.status === "PENDING"
  ).length;
  const failedNotifications = notifications.filter(
    (n) => n.status === "FAILED"
  ).length;

  const channelIcons: Record<string, typeof Mail> = {
    EMAIL: Mail,
    SLACK: MessageSquare,
    WEBHOOK: Webhook,
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="flex flex-col gap-4 rounded-3xl border border-border/70 bg-gradient-to-br from-pink-500/10 via-card to-card p-6 shadow-sm"
      >
        <div className="flex items-start gap-4">
          <div className="rounded-2xl bg-gradient-to-br from-pink-500 to-rose-600 p-3 text-white shadow-lg">
            <Bell className="h-6 w-6" />
          </div>
          <div className="flex-1">
            <h1 className="text-3xl font-semibold tracking-tight">
              Notification Center
            </h1>
            <p className="mt-2 text-base text-muted-foreground">
              Configure and monitor notifications via Email, Slack, and Webhooks
              for migration events.
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRetryFailed}
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry Failed
            </Button>
            <Button size="sm" onClick={() => setShowAddChannel(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Add Channel
            </Button>
          </div>
        </div>
      </motion.div>

      {showAddChannel && (
        <Card className="border-border/70 shadow-sm">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Add Notification Channel</CardTitle>
                <CardDescription>
                  Configure a new delivery method for alerts
                </CardDescription>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setShowAddChannel(false);
                  resetForm();
                }}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Channel Type</Label>
              <div className="flex gap-2">
                {(["EMAIL", "SLACK", "WEBHOOK"] as const).map((type) => {
                  const Icon = channelIcons[type];
                  return (
                    <Button
                      key={type}
                      variant={channelType === type ? "default" : "outline"}
                      size="sm"
                      onClick={() => setChannelType(type)}
                    >
                      <Icon className="mr-2 h-4 w-4" />
                      {type}
                    </Button>
                  );
                })}
              </div>
            </div>

            {channelType === "EMAIL" && (
              <div className="space-y-2">
                <Label>Email Address</Label>
                <Input
                  placeholder="alerts@company.com"
                  value={emailAddress}
                  onChange={(e) => setEmailAddress(e.target.value)}
                />
              </div>
            )}

            {channelType === "SLACK" && (
              <>
                <div className="space-y-2">
                  <Label>Slack Webhook URL</Label>
                  <Input
                    placeholder="https://hooks.slack.com/services/..."
                    value={slackWebhookUrl}
                    onChange={(e) => setSlackWebhookUrl(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Slack Channel</Label>
                  <Input
                    placeholder="#migrations-alerts"
                    value={slackChannel}
                    onChange={(e) => setSlackChannel(e.target.value)}
                  />
                </div>
              </>
            )}

            {channelType === "WEBHOOK" && (
              <div className="space-y-2">
                <Label>Webhook URL</Label>
                <Input
                  placeholder="https://api.example.com/webhook"
                  value={webhookUrl}
                  onChange={(e) => setWebhookUrl(e.target.value)}
                />
              </div>
            )}

            <div className="flex gap-2 pt-2">
              <Button
                onClick={handleCreateChannel}
                disabled={createConfigMutation.isPending}
              >
                {createConfigMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="mr-2 h-4 w-4" />
                )}
                Create Channel
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setShowAddChannel(false);
                  resetForm();
                }}
              >
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Sent</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-emerald-600">
              {sentNotifications}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Successfully delivered
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Pending</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-orange-600">
              {pendingNotifications}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Queued for delivery
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Failed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-red-600">
              {failedNotifications}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Delivery failed
            </p>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/70 shadow-sm">
        <CardHeader>
          <CardTitle>Notification Channels</CardTitle>
          <CardDescription>
            Configure delivery methods for migration events
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            {(["EMAIL", "SLACK", "WEBHOOK"] as const).map((type) => {
              const Icon = channelIcons[type];
              const labels = {
                EMAIL: { name: "Email", desc: "SMTP delivery", color: "blue" },
                SLACK: {
                  name: "Slack",
                  desc: "Webhook integration",
                  color: "purple",
                },
                WEBHOOK: {
                  name: "Webhook",
                  desc: "Custom endpoints",
                  color: "emerald",
                },
              };
              const cfg = labels[type];
              const configCount =
                userConfigsQuery.data?.filter(
                  (c) => c.notification_type === type
                ).length || 0;
              return (
                <div
                  key={type}
                  className="flex items-center gap-4 p-4 border border-border/70 rounded-2xl bg-background/50 hover:bg-muted/20 transition cursor-pointer"
                  onClick={() => {
                    setChannelType(type);
                    setShowAddChannel(true);
                  }}
                >
                  <div
                    className={`h-12 w-12 rounded-xl bg-${cfg.color}-500/10 flex items-center justify-center`}
                  >
                    <Icon
                      className={`h-6 w-6 text-${cfg.color}-600`}
                    />
                  </div>
                  <div>
                    <h4 className="font-semibold">{cfg.name}</h4>
                    <p className="text-sm text-muted-foreground">
                      {cfg.desc}
                    </p>
                    {configCount > 0 && (
                      <Badge variant="success" className="mt-1">
                        {configCount} configured
                      </Badge>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/70 shadow-sm">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Recent Notifications</CardTitle>
              <CardDescription>
                Delivery history for all notification events
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search notifications..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-8 w-56"
                />
              </div>
              <div className="flex items-center gap-1">
                <Filter className="h-4 w-4 text-muted-foreground" />
                <select
                  value={filterEventType}
                  onChange={(e) => setFilterEventType(e.target.value)}
                  className="h-10 rounded-2xl border border-border/70 bg-background/80 px-2 text-sm outline-none"
                >
                  <option value="">All Events</option>
                  {EVENT_TYPES.map((et) => (
                    <option key={et} value={et}>
                      {et}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {notificationHistoryQuery.isLoading && (
              <div className="space-y-2">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            )}
            {!notificationHistoryQuery.isLoading &&
              filteredNotifications.length === 0 && (
                <div className="py-6 text-center text-sm text-muted-foreground border border-dashed rounded-xl">
                  {searchTerm || filterEventType
                    ? "No notifications match your filters."
                    : "No notifications sent yet. Configure channels to start receiving alerts."}
                </div>
              )}
            {!notificationHistoryQuery.isLoading &&
              filteredNotifications.slice(0, 10).map((notification) => (
                <div
                  key={notification.id}
                  className="flex items-center justify-between p-4 border border-border/70 rounded-2xl bg-background/50 hover:bg-muted/20 transition"
                >
                  <div className="flex items-center gap-4">
                    <div
                      className={`h-10 w-10 rounded-xl flex items-center justify-center ${
                        notification.status === "SENT"
                          ? "bg-emerald-500/10 text-emerald-600"
                          : notification.status === "PENDING"
                          ? "bg-orange-500/10 text-orange-600"
                          : "bg-red-500/10 text-red-600"
                      }`}
                    >
                      {notification.status === "SENT" ? (
                        <CheckCircle2 className="h-5 w-5" />
                      ) : notification.status === "PENDING" ? (
                        <Clock className="h-5 w-5" />
                      ) : (
                        <XCircle className="h-5 w-5" />
                      )}
                    </div>
                    <div>
                      <h4 className="font-semibold">
                        {notification.subject}
                      </h4>
                      <p className="text-sm text-muted-foreground">
                        {notification.event_type}
                      </p>
                      {notification.error_message && (
                        <p className="text-xs text-red-600 mt-1">
                          {notification.error_message}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <Badge
                      variant={
                        notification.status === "SENT"
                          ? "success"
                          : notification.status === "PENDING"
                          ? "warning"
                          : "destructive"
                      }
                    >
                      {notification.status}
                    </Badge>
                    <div className="text-xs text-muted-foreground">
                      {notification.sent_at
                        ? new Date(notification.sent_at).toLocaleString()
                        : new Date(
                            notification.created_at
                          ).toLocaleString()}
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
