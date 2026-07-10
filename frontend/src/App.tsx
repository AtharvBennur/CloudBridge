import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/layout/AppShell";
import { ProtectedRoute } from "@/components/routing/ProtectedRoute";
import { AWSConnectionPage } from "@/pages/AWSConnectionPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { LoginPage } from "@/pages/LoginPage";
import { MigrationCreatePage } from "@/pages/MigrationCreatePage";
import { MigrationDetailPage } from "@/pages/MigrationDetailPage";
import { MigrationEditPage } from "@/pages/MigrationEditPage";
import { MigrationListPage } from "@/pages/MigrationListPage";
import { NotFoundPage } from "@/pages/NotFoundPage";

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
          path="/aws-connections"
          element={
            <ProtectedRoute>
              <AppShell>
                <AWSConnectionPage />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
}
