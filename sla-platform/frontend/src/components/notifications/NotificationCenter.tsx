import { useState } from "react";
import { Badge, Button, Drawer, List, Tag, Typography, Space } from "antd";
import {
  BellOutlined,
  CheckOutlined,
  DeleteOutlined,
} from "@ant-design/icons";
import { useNotificationStore, Notification } from "../../stores/notificationStore";
import dayjs from "dayjs";

const { Text, Paragraph } = Typography;

const levelColors: Record<string, string> = {
  info: "blue",
  warning: "orange",
  error: "red",
  success: "green",
};

export default function NotificationCenter() {
  const [open, setOpen] = useState(false);
  const {
    notifications,
    unreadCount,
    markRead,
    markAllRead,
    clearAll,
  } = useNotificationStore();

  return (
    <>
      <Badge count={unreadCount} size="small" offset={[-2, 2]}>
        <Button
          type="text"
          icon={<BellOutlined style={{ fontSize: 18, color: "#fff" }} />}
          onClick={() => setOpen(true)}
        />
      </Badge>
      <Drawer
        title={
          <Space style={{ width: "100%", justifyContent: "space-between" }}>
            <span>Notifications</span>
            <Space>
              <Button size="small" onClick={markAllRead}>
                <CheckOutlined /> Mark all read
              </Button>
              <Button size="small" danger onClick={clearAll}>
                <DeleteOutlined /> Clear
              </Button>
            </Space>
          </Space>
        }
        placement="right"
        width={400}
        open={open}
        onClose={() => setOpen(false)}
      >
        {notifications.length === 0 ? (
          <Text type="secondary">No notifications</Text>
        ) : (
          <List
            dataSource={notifications}
            renderItem={(item: Notification) => (
              <List.Item
                style={{
                  background: item.read ? "transparent" : "#f6f8ff",
                  cursor: "pointer",
                  padding: "12px 16px",
                }}
                onClick={() => markRead(item.id)}
              >
                <div style={{ width: "100%" }}>
                  <Space style={{ marginBottom: 4 }}>
                    <Tag color={levelColors[item.level] || "blue"}>
                      {item.level.toUpperCase()}
                    </Tag>
                    <Text strong>{item.title}</Text>
                  </Space>
                  <Paragraph
                    type="secondary"
                    style={{ margin: 0, fontSize: 13 }}
                    ellipsis={{ rows: 2 }}
                  >
                    {item.message}
                  </Paragraph>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {dayjs(item.timestamp * 1000).format("MMM D, HH:mm")}
                  </Text>
                </div>
              </List.Item>
            )}
          />
        )}
      </Drawer>
    </>
  );
}
