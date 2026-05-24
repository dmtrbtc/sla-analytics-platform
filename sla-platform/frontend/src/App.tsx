import { lazy, Suspense } from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { Spin } from "antd";
import AppLayout from "./components/layout/AppLayout";
import ProtectedRoute from "./components/auth/ProtectedRoute";
import RoleGuard from "./components/auth/RoleGuard";
import SLAConfig from "./pages/SLAConfig";
import RuntimeErrorBoundary from "./components/safety/RuntimeErrorBoundary";

const Dashboard = lazy(() => import("./pages/Dashboard"));
const DashboardExecutive = lazy(() => import("./pages/DashboardExecutive"));
const DashboardTeam = lazy(() => import("./pages/DashboardTeam"));
const DashboardOps = lazy(() => import("./pages/DashboardOps"));
const Wallboard = lazy(() => import("./pages/Wallboard"));
const Tickets = lazy(() => import("./pages/Tickets"));
const TicketDetail = lazy(() => import("./pages/TicketDetail"));
const Imports = lazy(() => import("./pages/Imports"));
const ImportDetail = lazy(() => import("./pages/ImportDetail"));
const ImportUpload = lazy(() => import("./pages/ImportUpload"));
const Reports = lazy(() => import("./pages/Reports"));
const AdminUsers = lazy(() => import("./pages/AdminUsers"));
const Login = lazy(() => import("./pages/Login"));
const NotFound = lazy(() => import("./pages/NotFound"));
const OperationsIncidents = lazy(() => import("./pages/OperationsIncidents"));
const SLAMonitor = lazy(() => import("./pages/SLAMonitor"));
const AdminDiagnostics = lazy(() => import("./pages/AdminDiagnostics"));
const SLACommandCenter = lazy(() => import("./pages/SLACommandCenter"));
const OperationsAdmin = lazy(() => import("./pages/OperationsAdmin"));
const TeamsPage = lazy(() => import("./pages/Teams"));
const SettingsPage = lazy(() => import("./pages/Settings"));
const QueueForensicsPage = lazy(() => import("./pages/QueueForensics"));
const ServiceDeskIntelligencePage = lazy(() => import("./pages/ServiceDeskIntelligence"));
const SLAForensicCommandCenter = lazy(() => import("./pages/SLAForensicCommandCenter"));
const FavoritesPage = lazy(() => import("./pages/Favorites"));
const SLALossCenter = lazy(() => import("./pages/SLALossCenter"));
const WorkplaceCommandCenter = lazy(() => import("./pages/WorkplaceCommandCenter"));
const AssetCommandCenter = lazy(() => import("./pages/AssetCommandCenter"));
const SLAReviewMode = lazy(() => import("./pages/SLAReviewMode"));
const WallboardOps = lazy(() => import("./pages/WallboardOps"));
const TicketTimelinePage = lazy(() => import("./pages/TicketTimelinePage"));
const SLAPortal = lazy(() => import("./pages/SLAPortal"));

/**
 * Wraps a route element in:
 *   1. RuntimeErrorBoundary — so a crash inside the page doesn't blank
 *      the entire SPA. The boundary is keyed by pathname so each route
 *      navigation resets a previous error state automatically.
 *   2. Suspense — so lazy chunk loading shows a spinner instead of
 *      flicker.
 *
 * Order matters: ErrorBoundary OUTSIDE Suspense — if the chunk itself
 * fails to load, the boundary catches the thrown promise.
 */
function SuspenseWrapper({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation();
  return (
    <RuntimeErrorBoundary label="страница" resetKey={pathname}>
      <Suspense fallback={<Spin size="large" style={{ display: "block", margin: "100px auto" }} />}>
        {children}
      </Suspense>
    </RuntimeErrorBoundary>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<SuspenseWrapper><Login /></SuspenseWrapper>} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/command-center" replace />} />
          <Route path="/command-center" element={<SuspenseWrapper><SLACommandCenter /></SuspenseWrapper>} />
          <Route path="/dashboard" element={<SuspenseWrapper><Dashboard /></SuspenseWrapper>} />
          <Route path="/dashboard/executive" element={<SuspenseWrapper><DashboardExecutive /></SuspenseWrapper>} />
          <Route path="/dashboard/teams" element={<SuspenseWrapper><DashboardTeam /></SuspenseWrapper>} />
          <Route path="/dashboard/ops" element={<SuspenseWrapper><DashboardOps /></SuspenseWrapper>} />
          <Route path="/wallboard" element={<SuspenseWrapper><Wallboard /></SuspenseWrapper>} />
          <Route path="/tickets" element={<SuspenseWrapper><Tickets /></SuspenseWrapper>} />
          <Route path="/tickets/:id" element={<SuspenseWrapper><TicketDetail /></SuspenseWrapper>} />
          <Route path="/imports" element={<SuspenseWrapper><Imports /></SuspenseWrapper>} />
          <Route path="/imports/:id" element={<SuspenseWrapper><ImportDetail /></SuspenseWrapper>} />
          <Route path="/imports/new" element={<SuspenseWrapper><ImportUpload /></SuspenseWrapper>} />
          <Route path="/reports" element={<SuspenseWrapper><Reports /></SuspenseWrapper>} />
          <Route path="/teams" element={<SuspenseWrapper><TeamsPage /></SuspenseWrapper>} />
          <Route path="/sla" element={<SuspenseWrapper><SLAConfig /></SuspenseWrapper>} />
          <Route path="/sla/portal" element={<SuspenseWrapper><SLAPortal /></SuspenseWrapper>} />
          <Route path="/sla/config" element={<SuspenseWrapper><SLAConfig /></SuspenseWrapper>} />
          <Route path="/sla/monitor" element={<SuspenseWrapper><SLAMonitor /></SuspenseWrapper>} />
          <Route path="/ops/incidents" element={<SuspenseWrapper><OperationsIncidents /></SuspenseWrapper>} />
          <Route path="/settings" element={<SuspenseWrapper><SettingsPage /></SuspenseWrapper>} />
          <Route path="/queue-forensics" element={<SuspenseWrapper><QueueForensicsPage /></SuspenseWrapper>} />
          <Route path="/servicedesk" element={<SuspenseWrapper><ServiceDeskIntelligencePage /></SuspenseWrapper>} />
          <Route path="/forensics" element={<SuspenseWrapper><SLAForensicCommandCenter /></SuspenseWrapper>} />
          <Route path="/favorites" element={<SuspenseWrapper><FavoritesPage /></SuspenseWrapper>} />
          <Route path="/sla-loss" element={<SuspenseWrapper><SLALossCenter /></SuspenseWrapper>} />
          <Route path="/ops/workplace" element={<SuspenseWrapper><WorkplaceCommandCenter /></SuspenseWrapper>} />
          <Route path="/ops/asset" element={<SuspenseWrapper><AssetCommandCenter /></SuspenseWrapper>} />
          <Route path="/review" element={<SuspenseWrapper><SLAReviewMode /></SuspenseWrapper>} />
          <Route path="/wallboard-ops/:domain" element={<SuspenseWrapper><WallboardOps /></SuspenseWrapper>} />
          <Route path="/tickets/:id/timeline" element={<SuspenseWrapper><TicketTimelinePage /></SuspenseWrapper>} />
          <Route path="/admin/users" element={<RoleGuard roles={["admin"]}><SuspenseWrapper><AdminUsers /></SuspenseWrapper></RoleGuard>} />
          <Route path="/admin/diagnostics" element={<RoleGuard roles={["admin"]}><SuspenseWrapper><AdminDiagnostics /></SuspenseWrapper></RoleGuard>} />
          <Route path="/admin/operations" element={<RoleGuard roles={["admin"]}><SuspenseWrapper><OperationsAdmin /></SuspenseWrapper></RoleGuard>} />
          <Route path="*" element={<SuspenseWrapper><NotFound /></SuspenseWrapper>} />
        </Route>
      </Route>
    </Routes>
  );
}
