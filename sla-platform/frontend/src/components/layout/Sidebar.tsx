import { useNavigate, useLocation } from "react-router-dom";
import { Layout, Menu } from "antd";
import {
  DashboardOutlined, FileTextOutlined, UploadOutlined, TeamOutlined,
  ClockCircleOutlined, SettingOutlined, FundOutlined, ExclamationCircleOutlined,
  BugOutlined, AimOutlined, ControlOutlined, RadarChartOutlined, ThunderboltOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { useAuthStore } from "../../stores/authStore";

const { Sider } = Layout;

export default function Sidebar() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((s) => s.user);

  const menuItems = [
    { key: "/command-center", icon: <RadarChartOutlined />, label: t("nav.commandCenter", "Командный центр") },
    { key: "/dashboard", icon: <DashboardOutlined />, label: t("nav.dashboard") },
    { key: "/dashboard/executive", icon: <FundOutlined />, label: t("nav.executive", "Executive") },
    { key: "/dashboard/ops", icon: <ThunderboltOutlined />, label: t("nav.analytics") },
    { key: "/dashboard/teams", icon: <TeamOutlined />, label: t("nav.teamDashboard") },
    { key: "/tickets", icon: <FileTextOutlined />, label: t("nav.tickets") },
    { key: "/imports", icon: <UploadOutlined />, label: t("nav.imports") },
    { key: "/sla/config", icon: <ClockCircleOutlined />, label: t("nav.slaConfig") },
    { key: "/sla/monitor", icon: <AimOutlined />, label: t("nav.slaMonitor") },
    { key: "/ops/incidents", icon: <ExclamationCircleOutlined />, label: t("nav.incidents") },
    { key: "/reports", icon: <FileTextOutlined />, label: t("nav.reports") },
    { key: "/teams", icon: <TeamOutlined />, label: t("nav.teamsConfig") },
    ...(user?.role === "admin"
      ? [
          { key: "/admin/operations", icon: <ControlOutlined />, label: t("nav.operations", "Operations") },
          { key: "/admin/users", icon: <SettingOutlined />, label: t("nav.admin") },
          { key: "/admin/diagnostics", icon: <BugOutlined />, label: t("nav.diagnostics") },
        ]
      : []),
  ];

  const selectedKey = menuItems.find(item => location.pathname.startsWith(item.key))?.key || "/command-center";

  return (
    <Sider collapsible>
      <div style={{ color: "#fff", padding: "12px 16px", fontWeight: 700, fontSize: 14, letterSpacing: "-0.01em", whiteSpace: "nowrap", overflow: "hidden" }}>
        SLA Platform
      </div>
      <Menu theme="dark" mode="inline" selectedKeys={[selectedKey]} items={menuItems} onClick={({ key }) => navigate(key)} />
    </Sider>
  );
}
