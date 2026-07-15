import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Bell, Mail, MessageSquare, Webhook, Plus, RefreshCw, CheckCircle2, XCircle, Clock } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { notificationService } from "@/services/notificationService";

export function NotificationsPage() {
  const notificationHistoryQuery = useQuery({
    queryKey: ["notification-history"],
    queryFn: () => notificationService.getHistory({ limit: 50 }),
  });

  const handleRetryFailed = async () => {
    try {
      await notificationService.retryFailed();
      notificationHistoryQuery.refetch();
    } catch (error) {
      console.error("Failed to retry notifications:", error);
    }
  };

  const notifications = notificationHistoryQuery.data || [];
  const sentNotifications = notifications.filter(n => n.status === "SENT").length;
  const pendingNotifications = notifications.filter(n => n.status === "PENDING").length;
  const failedNotifications = notifications.filter(n => n.status === "FAILED").length;

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
            <h1 className="text-3xl font-semibold tracking-tight">Notification Center</h1>
            <p className="mt-2 text-base text-muted-foreground">
              Configure and monitor notifications via Email, Slack, and Webhooks for migration events.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleRetryFailed}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry Failed
            </Button>
            <Button size="sm">
              <Plus className="mr-2 h-4 w-4" />
              Add Channel
            </Button>
          </div>
        </div>
      </motion.div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Sent</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-emerald-600">{sentNotifications}</div>
            <p className="text-xs text-muted-foreground mt-1">Successfully delivered</p>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Pending</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-orange-600">{pendingNotifications}</div>
            <p className="text-xs text-muted-foreground mt-1">Queued for delivery</p>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Failed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-red-600">{failedNotifications}</div>
            <p className="text-xs text-muted-foreground mt-1">Delivery failed</p>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/70 shadow-sm">
        <CardHeader>
          <CardTitle>Notification Channels</CardTitle>
          <CardDescription>Configure delivery methods for migration events</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="flex items-center gap-4 p-4 border border-border/70 rounded-2xl bg-background/50 hover:bg-muted/20 transition cursor-pointer">
              <div className="h-12 w-12 rounded-xl bg-blue-500/10 flex items-center justify-center">
                <Mail className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <h4 className="font-semibold">Email</h4>
                <p className="text-sm text-muted-foreground">SMTP delivery</p>
              </div>
            </div>
            <div className="flex items-center gap-4 p-4 border border-border/70 rounded-2xl bg-background/50 hover:bg-muted/20 transition cursor-pointer">
              <div className="h-12 w-12 rounded-xl bg-purple-500/10 flex items-center justify-center">
                <MessageSquare className="h-6 w-6 text-purple-600" />
              </div>
              <div>
                <h4 className="font-semibold">Slack</h4>
                <p className="text-sm text-muted-foreground">Webhook integration</p>
              </div>
            </div>
            <div className="flex items-center gap-4 p-4 border border-border/70 rounded-2xl bg-background/50 hover:bg-muted/20 transition cursor-pointer">
              <div className="h-12 w-12 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                <Webhook className="h-6 w-6 text-emerald-600" />
              </div>
              <div>
                <h4 className="font-semibold">Webhook</h4>
                <p className="text-sm text-muted-foreground">Custom endpoints</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/70 shadow-sm">
        <CardHeader>
          <CardTitle>Recent Notifications</CardTitle>
          <CardDescription>Delivery history for all notification events</CardDescription>
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
            {!notificationHistoryQuery.isLoading && notifications.length === 0 && (
              <div className="py-6 text-center text-sm text-muted-foreground border border-dashed rounded-xl">
                No notifications sent yet. Configure channels to start receiving alerts.
              </div>
            )}
            {!notificationHistoryQuery.isLoading && notifications.slice(0, 10).map((notification) => (
              <div key={notification.id} className="flex items-center justify-between p-4 border border-border/70 rounded-2xl bg-background/50 hover:bg-muted/20 transition">
                <div className="flex items-center gap-4">
                  <div className={`h-10 w-10 rounded-xl flex items-center justify-center ${
                    notification.status === "SENT" ? "bg-emerald-500/10 text-emerald-600" :
                    notification.status === "PENDING" ? "bg-orange-500/10 text-orange-600" :
                    "bg-red-500/10 text-red-600"
                  }`}>
                    {notification.status === "SENT" ? (
                      <CheckCircle2 className="h-5 w-5" />
                    ) : notification.status === "PENDING" ? (
                      <Clock className="h-5 w-5" />
                    ) : (
                      <XCircle className="h-5 w-5" />
                    )}
                  </div>
                  <div>
                    <h4 className="font-semibold">{notification.subject}</h4>
                    <p className="text-sm text-muted-foreground">{notification.event_type}</p>
                    {notification.error_message && (
                      <p className="text-xs text-red-600 mt-1">{notification.error_message}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <Badge variant={notification.status === "SENT" ? "success" : notification.status === "PENDING" ? "warning" : "destructive"}>
                    {notification.status}
                  </Badge>
                  <div className="text-xs text-muted-foreground">
                    {notification.sent_at ? new Date(notification.sent_at).toLocaleString() : new Date(notification.created_at).toLocaleString()}
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
