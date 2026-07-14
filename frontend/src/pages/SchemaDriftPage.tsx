import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { GitCompare, AlertTriangle, CheckCircle2, Clock, Database, Plus, Camera } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function SchemaDriftPage() {
  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="flex flex-col gap-4 rounded-3xl border border-border/70 bg-gradient-to-br from-orange-500/10 via-card to-card p-6 shadow-sm"
      >
        <div className="flex items-start gap-4">
          <div className="rounded-2xl bg-gradient-to-br from-orange-500 to-red-500 p-3 text-white shadow-lg">
            <GitCompare className="h-6 w-6" />
          </div>
          <div className="flex-1">
            <h1 className="text-3xl font-semibold tracking-tight">Schema Drift Detection</h1>
            <p className="mt-2 text-base text-muted-foreground">
              Monitor and detect schema changes in real-time with automatic drift analysis and approval workflows.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm">
              <Camera className="mr-2 h-4 w-4" />
              Capture Snapshot
            </Button>
            <Button size="sm">
              <Plus className="mr-2 h-4 w-4" />
              Compare Schemas
            </Button>
          </div>
        </div>
      </motion.div>

      <div className="grid gap-6 lg:grid-cols-4">
        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Total Changes</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold">24</div>
            <p className="text-xs text-muted-foreground mt-1">Detected this week</p>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Pending Approval</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-orange-600">7</div>
            <p className="text-xs text-muted-foreground mt-1">Awaiting review</p>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Auto-Applied</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-emerald-600">15</div>
            <p className="text-xs text-muted-foreground mt-1">Safe changes</p>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Rejected</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-red-600">2</div>
            <p className="text-xs text-muted-foreground mt-1">Blocked changes</p>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/70 shadow-sm">
        <CardHeader>
          <CardTitle>Recent Schema Changes</CardTitle>
          <CardDescription>Latest detected schema drift events requiring attention</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[
              { type: "ADD_COLUMN", table: "users", column: "phone_number", risk: "SAFE", status: "APPLIED" },
              { type: "DROP_COLUMN", table: "orders", column: "legacy_id", risk: "HIGH", status: "PENDING" },
              { type: "CREATE_INDEX", table: "products", column: "sku_idx", risk: "SAFE", status: "APPLIED" },
              { type: "ALTER_TABLE", table: "transactions", column: "amount", risk: "HIGH", status: "PENDING" },
            ].map((change, index) => (
              <div key={index} className="flex items-center justify-between p-4 border border-border/70 rounded-2xl bg-background/50 hover:bg-muted/20 transition">
                <div className="flex items-center gap-4">
                  <div className={`h-10 w-10 rounded-xl flex items-center justify-center ${
                    change.risk === "SAFE" ? "bg-emerald-500/10 text-emerald-600" : 
                    change.risk === "HIGH" ? "bg-red-500/10 text-red-600" : 
                    "bg-orange-500/10 text-orange-600"
                  }`}>
                    <Database className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="font-semibold">{change.type.replace('_', ' ')}</h4>
                    <p className="text-sm text-muted-foreground">
                      Table: {change.table} {change.column ? `• ${change.column}` : ''}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <Badge variant={change.risk === "SAFE" ? "success" : change.risk === "HIGH" ? "destructive" : "warning"}>
                    {change.risk}
                  </Badge>
                  <Badge variant={change.status === "APPLIED" ? "success" : "secondary"}>
                    {change.status}
                  </Badge>
                  {change.status === "PENDING" && (
                    <div className="flex gap-2">
                      <Button variant="ghost" size="sm">Approve</Button>
                      <Button variant="ghost" size="sm">Reject</Button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
