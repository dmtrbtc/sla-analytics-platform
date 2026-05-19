import { useNavigate, useLocation } from "react-router-dom";
import { Layout, Menu } from "antd";
import {
  DashboardOutlined,
  FileTextOutlined,
  UploadOutlined,
  TeamOutlined,
  ClockCircleOutlined,
  SettingOutlined,
  FundOutlined,
  ExclamationCircleOutlined,
  BugOutlined,
  AimOutlined,
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
    { key: "/dashboard", icon: <DashboardOutlined />, label: t("nav.dashboard") },
    { key: "/dashboard/ops", icon: <FundOutlined />, label: t("nav.analytics") },
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
          { key: "/admin/users", icon: <SettingOutlined />, label: t("nav.admin") },
          { key: "/admin/diagnostics", icon: <BugOutlined />, label: t("nav.diagnostics") },
        ]
      : []),
  ];

  return (
    <Sider collapsible>
      <div
        style={{
          color: "#fff",
          padding: 16,
          fontWeight: "bold",
          fontSize: 16,
        }}
      >
        {t("app.platform")}
      </div>
      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[location.pathname]}
        items={menuItems}
        onClick={({ key }) => navigate(key)}
      />
    </Sider>
  );
}
