import { useNavigate, useLocation } from "react-router-dom";
import { Layout, Menu, Typography } from "antd";
import {
  DashboardOutlined, FileTextOutlined, UploadOutlined, TeamOutlined,
  ClockCircleOutlined, SettingOutlined, FundOutlined, ExclamationCircleOutlined,
  BugOutlined, AimOutlined, ControlOutlined, RadarChartOutlined, ThunderboltOutlined,
  UserOutlined, BarChartOutlined, SafetyOutlined, PaperClipOutlined,
  ApartmentOutlined, HeatMapOutlined, NodeIndexOutlined,
  StarFilled,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { useAuthStore } from "../../stores/authStore";

const { Sider } = Layout;
const { Text } = Typography;

export default function Sidebar() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((s) => s.user);
  const isAdmin = user?.role === "admin";

  const mainItems = [
    { key: "/dashboard", icon: <DashboardOutlined />, label: t("nav.dashboard") },
    { key: "/favorites", icon: <StarFilled style={{ color: "#f5c518" }} />, label: "Избранное" },
    { key: "/dashboard/executive", icon: <FundOutlined />, label: t("nav.executive", "Executive") },
    { key: "/dashboard/ops", icon: <ThunderboltOutlined />, label: t("nav.analytics") },
    { key: "/dashboard/teams", icon: <BarChartOutlined />, label: t("nav.teamDashboard") },
  ];

  const queueIntelItems = [
    { key: "/command-center", icon: <RadarChartOutlined />, label: "OTRS Command Center" },
    { key: "/queue-forensics", icon: <HeatMapOutlined />, label: "Queue Forensics" },
    { key: "/servicedesk", icon: <ApartmentOutlined />, label: "ServiceDesk Intel" },
    { key: "/forensics", icon: <RadarChartOutlined />, label: "Форензика SLA V3" },
    { key: "/sla-loss", icon: <HeatMapOutlined />, label: "Где теряется SLA" },
  ];

  const opsItems = [
    { key: "/tickets", icon: <FileTextOutlined />, label: t("nav.tickets") },
    { key: "/imports", icon: <UploadOutlined />, label: t("nav.imports") },
    { key: "/reports", icon: <PaperClipOutlined />, label: t("nav.reports") },
    { key: "/sla/config", icon: <ClockCircleOutlined />, label: t("nav.slaConfig") },
    { key: "/sla/monitor", icon: <AimOutlined />, label: t("nav.slaMonitor") },
    { key: "/ops/incidents", icon: <ExclamationCircleOutlined />, label: t("nav.incidents") },
  ];

  const adminItems = isAdmin ? [
    { type: "divider" as const },
    { key: "admin-header", icon: <SafetyOutlined />, label: <Text style={{ color: "rgba(255,255,255,0.45)", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em" }}>Admin</Text>, disabled: true },
    { key: "/admin/users", icon: <UserOutlined />, label: t("nav.admin") },
    { key: "/teams", icon: <TeamOutlined />, label: t("nav.teamsConfig") },
    { key: "/admin/operations", icon: <ControlOutlined />, label: t("nav.operations", "Operations") },
    { key: "/admin/diagnostics", icon: <BugOutlined />, label: t("nav.diagnostics") },
    { key: "/settings", icon: <SettingOutlined />, label: t("nav.settings", "Настройки") },
  ] : [];

  const menuItems = [
    { type: "group" as const, label: <Text style={{ color: "rgba(255,255,255,0.45)", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em" }}>Навигация</Text>, children: mainItems },
    { type: "group" as const, label: <Text style={{ color: "rgba(255,255,255,0.45)", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em" }}>Queue Intelligence</Text>, children: queueIntelItems },
    { type: "group" as const, label: <Text style={{ color: "rgba(255,255,255,0.45)", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em" }}>Операции</Text>, children: opsItems },
    ...adminItems,
  ];

  return (
    <Sider collapsible>
      <div style={{ color: "#fff", padding: "12px 16px 8px", fontWeight: 700, fontSize: 14, letterSpacing: "-0.01em", whiteSpace: "nowrap", overflow: "hidden", borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
        SLA Platform
      </div>
      <Menu theme="dark" mode="inline" selectedKeys={[location.pathname]} defaultOpenKeys={["main", "ops"]}
        items={menuItems} onClick={({ key }) => navigate(key)} style={{ borderRight: 0 }} />
    </Sider>
  );
}
