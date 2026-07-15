import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/layout/AppShell";
import { ProtectedRoute } from "@/components/routing/ProtectedRoute";
import { AWSConnectionPage } from "@/pages/AWSConnectionPage";
import { DatabaseConfigPage } from "@/pages/DatabaseConfigPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { LoginPage } from "@/pages/LoginPage";
import { MigrationCreatePage } from "@/pages/MigrationCreatePage";
import { MigrationDetailPage } from "@/pages/MigrationDetailPage";
import { MigrationEditPage } from "@/pages/MigrationEditPage";
import { MigrationListPage } from "@/pages/MigrationListPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { PreflightPage } from "@/pages/PreflightPage";
import { CDCPage } from "@/pages/CDCPage";
import { SchemaDriftPage } from "@/pages/SchemaDriftPage";
import { ApprovalsPage } from "@/pages/ApprovalsPage";
import { ECSPage } from "@/pages/ECSPage";
import { ObservabilityPage } from "@/pages/ObservabilityPage";
import { NotificationsPage } from "@/pages/NotificationsPage";
import { RollbackPage } from "@/pages/RollbackPage";
import { AccountPage } from "@/pages/AccountPage";
import { SettingsPage } from "@/pages/SettingsPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <AppShell>
                <DashboardPage />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/migrations"
          element={
            <ProtectedRoute>
              <AppShell>
                <MigrationListPage />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/migrations/new"
          element={
            <ProtectedRoute>
              <AppShell>
                <MigrationCreatePage />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/migrations/:id"
          element={
            <ProtectedRoute>
              <AppShell>
                <MigrationDetailPage />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/migrations/:id/edit"
          element={
            <ProtectedRoute>
              <AppShell>
                <MigrationEditPage />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/database-configs"
          element={
            <ProtectedRoute>
              <AppShell>
                <DatabaseConfigPage />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/aws-connections"
          element={
            <ProtectedRoute>
              <AppShell>
                <AWSConnectionPage />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route path="/preflight" element={<ProtectedRoute><AppShell><PreflightPage /></AppShell></ProtectedRoute>} />
        <Route path="/cdc" element={<ProtectedRoute><AppShell><CDCPage /></AppShell></ProtectedRoute>} />
        <Route path="/schema-drift" element={<ProtectedRoute><AppShell><SchemaDriftPage /></AppShell></ProtectedRoute>} />
        <Route path="/approvals" element={<ProtectedRoute><AppShell><ApprovalsPage /></AppShell></ProtectedRoute>} />
        <Route path="/ecs" element={<ProtectedRoute><AppShell><ECSPage /></AppShell></ProtectedRoute>} />
        <Route path="/observability" element={<ProtectedRoute><AppShell><ObservabilityPage /></AppShell></ProtectedRoute>} />
        <Route path="/notifications" element={<ProtectedRoute><AppShell><NotificationsPage /></AppShell></ProtectedRoute>} />
        <Route path="/rollback" element={<ProtectedRoute><AppShell><RollbackPage /></AppShell></ProtectedRoute>} />
        <Route path="/account" element={<ProtectedRoute><AppShell><AccountPage /></AppShell></ProtectedRoute>} />
        <Route path="/settings" element={<ProtectedRoute><AppShell><SettingsPage /></AppShell></ProtectedRoute>} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
}
