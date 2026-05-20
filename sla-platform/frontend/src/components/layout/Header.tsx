import { useState } from "react";
import { Layout, Button, Dropdown, Space, Tag, Switch, Tooltip } from "antd";
import { MenuFoldOutlined, MenuUnfoldOutlined, UserOutlined, LogoutOutlined, BellOutlined, SettingOutlined, SunOutlined, MoonOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { useAuthStore } from "../../stores/authStore";
import { useUIStore } from "../../stores/uiStore";
import { useTheme } from "../../design/ThemeContext";
import { useNavigate } from "react-router-dom";
import { palette } from "../../design/colors";
import { layout } from "../../design/spacing";
import { shadows } from "../../design/shadows";

const { Header: AntHeader } = Layout;

export default function Header() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { sidebarCollapsed, toggleSidebar } = useUIStore();
  const { user, logout } = useAuthStore();
  const { resolved, setMode, mode } = useTheme();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <AntHeader
      style={{
        height: layout.headerHeight,
        lineHeight: layout.headerHeight,
        background: palette.white,
        borderBottom: `1px solid ${palette.borderLight}`,
        boxShadow: shadows.toolbar,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 20px",
        position: "sticky",
        top: 0,
        zIndex: 100,
      }}
    >
      <Space>
        <Button
          type="text"
          icon={sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          onClick={toggleSidebar}
          style={{ fontSize: 14, width: 32, height: 32, display: "flex", alignItems: "center", justifyContent: "center" }}
        />
      </Space>

      <Space size="middle">
        <Tooltip title={resolved === "dark" ? "Светлая тема" : "Тёмная тема"}>
          <Switch
            checkedChildren={<MoonOutlined />}
            unCheckedChildren={<SunOutlined />}
            checked={resolved === "dark"}
            onChange={(checked) => setMode(checked ? "dark" : "light")}
            style={{ background: resolved === "dark" ? "#30363d" : "#e1e4e8" }}
          />
        </Tooltip>

        <Dropdown
          menu={{
            items: [
              { key: "profile", icon: <UserOutlined />, label: user?.display_name || user?.email },
              { type: "divider" },
              { key: "logout", icon: <LogoutOutlined />, label: t("auth.logout"), onClick: handleLogout },
            ],
          }}
        >
          <Button type="text" icon={<UserOutlined />} style={{ fontSize: 13 }}>
            <Tag color="blue" style={{ fontSize: 11, borderRadius: 4, marginLeft: 4 }}>{user?.role}</Tag>
          </Button>
        </Dropdown>
      </Space>
    </AntHeader>
  );
}
