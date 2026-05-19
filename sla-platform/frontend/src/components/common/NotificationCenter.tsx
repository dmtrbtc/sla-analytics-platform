import { useState, useCallback } from "react";
import { Badge, Popover, Button, List, Typography, Space, Tag, Empty } from "antd";
import { BellOutlined, WarningOutlined, FireOutlined, CheckCircleOutlined, InfoCircleOutlined } from "@ant-design/icons";
import { palette } from "../../design/colors";

interface Notification {
  id: string;
  type: "breach" | "risk" | "overload" | "info";
  title: string;
  queue: string;
  time: string;
  read: boolean;
}

const MOCK_NOTIFICATIONS: Notification[] = [
  { id: "1", type: "breach", title: "Support Queue SLA breach", queue: "Support", time: "2 мин назад", read: false },
  { id: "2", type: "risk", title: "Billing — 95% SLA usage", queue: "Billing", time: "5 мин назад", read: false },
  { id: "3", type: "overload", title: "Infrastructure перегружена", queue: "Infrastructure", time: "12 мин назад", read: false },
  { id: "4", type: "info", title: "Отчёт Executive сгенерирован", queue: "System", time: "30 мин назад", read: true },
  { id: "5", type: "breach", title: "Security — нарушение реакции", queue: "Security", time: "1 ч назад", read: true },
];

const iconMap: Record<string, React.ReactNode> = {
  breach: <FireOutlined style={{ color: palette.accent.rose }} />,
  risk: <WarningOutlined style={{ color: palette.accent.amber }} />,
  overload: <WarningOutlined style={{ color: palette.accent.amber }} />,
  info: <InfoCircleOutlined style={{ color: palette.brand[500] }} />,
};

const tagColorMap: Record<string, string> = {
  breach: "red",
  risk: "orange",
  overload: "orange",
  info: "blue",
};

export function NotificationCenter() {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState(MOCK_NOTIFICATIONS);
  const unread = notifications.filter((n) => !n.read).length;

  const markAllRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  }, []);

  return (
    <Popover
      open={open}
      onOpenChange={setOpen}
      trigger="click"
      placement="bottomRight"
      arrow={false}
      content={
        <div style={{ width: 360, maxHeight: 400, overflow: "auto" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 12px", borderBottom: `1px solid ${palette.borderLight}` }}>
            <Typography.Text strong style={{ fontSize: 13 }}>Уведомления</Typography.Text>
            <Button size="small" type="link" onClick={markAllRead} style={{ fontSize: 11 }}>
              Прочитано
            </Button>
          </div>
          {notifications.length > 0 ? (
            <List
              dataSource={notifications}
              renderItem={(item) => (
                <List.Item
                  style={{
                    padding: "10px 12px",
                    cursor: "pointer",
                    background: item.read ? "transparent" : palette.page,
                    borderBottom: `1px solid ${palette.borderLight}`,
                    transition: "background 0.2s",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = palette.page)}
                  onMouseLeave={(e) => (e.currentTarget.style.background = item.read ? "transparent" : palette.page)}
                >
                  <Space size={8}>
                    {iconMap[item.type]}
                    <div>
                      <div style={{ fontSize: 13, color: palette.text.primary }}>{item.title}</div>
                      <Space size={6}>
                        <Tag color={tagColorMap[item.type]} style={{ fontSize: 10, lineHeight: "16px", padding: "0 4px" }}>{item.queue}</Tag>
                        <span style={{ fontSize: 11, color: palette.text.tertiary }}>{item.time}</span>
                      </Space>
                    </div>
                  </Space>
                </List.Item>
              )}
            />
          ) : (
            <Empty description="Нет уведомлений" image={Empty.PRESENTED_IMAGE_SIMPLE} style={{ padding: 24 }} />
          )}
        </div>
      }
    >
      <Badge count={unread} size="small" offset={[-2, 2]}>
        <Button type="text" icon={<BellOutlined style={{ fontSize: 16, color: palette.text.secondary }} />} />
      </Badge>
    </Popover>
  );
}
