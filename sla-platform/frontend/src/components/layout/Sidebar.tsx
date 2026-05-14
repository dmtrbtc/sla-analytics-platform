import { useNavigate, useLocation } from "react-router-dom";
import { Layout, Menu } from "antd";
import {
  DashboardOutlined,
  FileTextOutlined,
  UploadOutlined,
  TeamOutlined,
  ClockCircleOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import { useAuthStore } from "../../stores/authStore";

const { Sider } = Layout;

export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((s) => s.user);

  const menuItems = [
    { key: "/dashboard", icon: <DashboardOutlined />, label: "Dashboard" },
    { key: "/dashboard/teams", icon: <TeamOutlined />, label: "Team Dashboard" },
    { key: "/tickets", icon: <FileTextOutlined />, label: "Tickets" },
    { key: "/imports", icon: <UploadOutlined />, label: "Imports" },
    { key: "/sla", icon: <ClockCircleOutlined />, label: "SLA" },
    { key: "/reports", icon: <FileTextOutlined />, label: "Reports" },
    { key: "/teams", icon: <TeamOutlined />, label: "Teams Config" },
    ...(user?.role === "admin"
      ? [{ key: "/admin/users", icon: <SettingOutlined />, label: "Admin" }]
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
        SLA Platform
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
