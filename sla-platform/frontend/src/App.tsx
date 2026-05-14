import { Routes, Route, Navigate } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";
import ProtectedRoute from "./components/auth/ProtectedRoute";
import RoleGuard from "./components/auth/RoleGuard";
import Dashboard from "./pages/Dashboard";
import DashboardTeam from "./pages/DashboardTeam";
import Tickets from "./pages/Tickets";
import TicketDetail from "./pages/TicketDetail";
import Imports from "./pages/Imports";
import ImportDetail from "./pages/ImportDetail";
import ImportUpload from "./pages/ImportUpload";
import Reports from "./pages/Reports";
import Teams from "./pages/Teams";
import SLAConfig from "./pages/SLAConfig";
import AdminUsers from "./pages/AdminUsers";
import Login from "./pages/Login";
import NotFound from "./pages/NotFound";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/dashboard/teams" element={<DashboardTeam />} />
          <Route path="/tickets" element={<Tickets />} />
          <Route path="/tickets/:id" element={<TicketDetail />} />
          <Route path="/imports" element={<Imports />} />
          <Route path="/imports/:id" element={<ImportDetail />} />
          <Route path="/imports/new" element={<ImportUpload />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/teams" element={<Teams />} />
          <Route path="/sla" element={<SLAConfig />} />
          <Route
            path="/admin/users"
            element={
              <RoleGuard roles={["admin"]}>
                <AdminUsers />
              </RoleGuard>
            }
          />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Route>
    </Routes>
  );
}
