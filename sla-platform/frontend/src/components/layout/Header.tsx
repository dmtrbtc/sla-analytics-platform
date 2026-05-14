import { Layout, Button, Typography } from "antd";
import { MenuFoldOutlined, MenuUnfoldOutlined, LogoutOutlined } from "@ant-design/icons";
import { useUIStore } from "../../stores/uiStore";
import { useAuth } from "../../hooks/useAuth";

const { Header: AntHeader } = Layout;

export default function Header() {
  const { sidebarCollapsed, toggleSidebar } = useUIStore();
  const { user, logout } = useAuth();

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
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <Typography.Text>{user?.display_name || "User"}</Typography.Text>
        <Button type="text" icon={<LogoutOutlined />} onClick={logout} />
      </div>
    </AntHeader>
  );
}
