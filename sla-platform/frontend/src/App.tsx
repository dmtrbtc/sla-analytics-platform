import { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Spin } from "antd";
import AppLayout from "./components/layout/AppLayout";
import ProtectedRoute from "./components/auth/ProtectedRoute";
import RoleGuard from "./components/auth/RoleGuard";
import Teams from "./pages/Teams";
import SLAConfig from "./pages/SLAConfig";

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

function SuspenseWrapper({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<Spin size="large" style={{ display: "block", margin: "100px auto" }} />}>{children}</Suspense>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<SuspenseWrapper><Login /></SuspenseWrapper>} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
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
          <Route path="/teams" element={<Teams />} />
          <Route path="/sla" element={<SLAConfig />} />
          <Route path="/sla/config" element={<SLAConfig />} />
          <Route path="/sla/monitor" element={<SuspenseWrapper><SLAMonitor /></SuspenseWrapper>} />
          <Route path="/ops/incidents" element={<SuspenseWrapper><OperationsIncidents /></SuspenseWrapper>} />
          <Route
            path="/admin/users"
            element={
              <RoleGuard roles={["admin"]}>
                <SuspenseWrapper><AdminUsers /></SuspenseWrapper>
              </RoleGuard>
            }
          />
          <Route
            path="/admin/diagnostics"
            element={
              <RoleGuard roles={["admin"]}>
                <SuspenseWrapper><AdminDiagnostics /></SuspenseWrapper>
              </RoleGuard>
            }
          />
          <Route path="*" element={<SuspenseWrapper><NotFound /></SuspenseWrapper>} />
        </Route>
      </Route>
    </Routes>
  );
}
