import { Layout, Button, Typography, Dropdown, Space, Tag } from "antd";
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  LogoutOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { useUIStore } from "../../stores/uiStore";
import { useAuthStore } from "../../stores/authStore";
import { authApi } from "../../api/auth";
import NotificationCenter from "../notifications/NotificationCenter";
import { DemoModeToggle } from "../common/DemoModeToggle";

const { Header: AntHeader } = Layout;

const ROLE_COLORS: Record<string, string> = {
  admin: "red",
  analyst: "blue",
  viewer: "green",
};

export default function Header() {
  const { t } = useTranslation();
  const { sidebarCollapsed, toggleSidebar } = useUIStore();
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch {
      // ignore
    }
    logout();
    navigate("/login", { replace: true });
  };

  const items = [
    {
      key: "profile",
      label: (
        <Space>
          <UserOutlined />
          {user?.display_name || t("auth.user")}
          {user?.role && (
            <Tag color={ROLE_COLORS[user.role]} style={{ margin: 0 }}>
              {user.role}
            </Tag>
          )}
        </Space>
      ),
      disabled: true,
    },
    { type: "divider" as const },
    {
      key: "logout",
      icon: <LogoutOutlined />,
      label: t("header.signOut"),
      onClick: handleLogout,
    },
  ];

  return (
    <AntHeader
      style={{
        background: "#fff",
        padding: "0 24px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        borderBottom: "1px solid #f0f0f0",
      }}
    >
      <Button
        type="text"
        icon={sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
        onClick={toggleSidebar}
      />
      <Space>
        <DemoModeToggle />
        <NotificationCenter />
        <Dropdown menu={{ items }} placement="bottomRight">
          <Button type="text" style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <UserOutlined />
            <Typography.Text>{user?.display_name || t("auth.user")}</Typography.Text>
          </Button>
        </Dropdown>
      </Space>
    </AntHeader>
  );
}
