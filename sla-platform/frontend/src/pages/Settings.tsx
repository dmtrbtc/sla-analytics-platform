import { Typography, Card, Row, Col, Tag, Space, Divider, List } from "antd";
import { SettingOutlined, SafetyOutlined, BellOutlined, CalendarOutlined, TeamOutlined, UserOutlined, CloudServerOutlined, ExportOutlined, BugOutlined, SlidersOutlined, AimOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useTheme } from "../design/ThemeContext";
import { cardStyle, cardHeaderStyle } from "../design/tokens";
import { spacing } from "../design/spacing";

const { Text, Title } = Typography;

const sections = [
  { key: "general", icon: <SlidersOutlined />, title: "Общие", desc: "Название платформы, язык, часовой пояс", path: "/settings/general" },
  { key: "sla", icon: <AimOutlined />, title: "SLA", desc: "Правила, календари, эскалации", path: "/sla/config" },
  { key: "teams", icon: <TeamOutlined />, title: "Команды", desc: "Управление командами и участниками", path: "/teams" },
  { key: "users", icon: <UserOutlined />, title: "Пользователи", desc: "Учётные записи, роли, разрешения", path: "/admin/users" },
  { key: "security", icon: <SafetyOutlined />, title: "Безопасность", desc: "SSO, SAML, аудит, шифрование экспорта", path: "/admin/diagnostics" },
  { key: "integrations", icon: <CloudServerOutlined />, title: "Интеграции", desc: "Slack, Teams, Jira, OTRS, вебхуки", path: "/settings" },
  { key: "notifications", icon: <BellOutlined />, title: "Уведомления", desc: "Каналы оповещений, подписки", path: "/settings" },
  { key: "calendars", icon: <CalendarOutlined />, title: "Календари", desc: "Рабочее время, праздники", path: "/sla/config" },
  { key: "exports", icon: <ExportOutlined />, title: "Экспорт", desc: "Форматы отчётов, брендирование", path: "/reports" },
  { key: "diagnostics", icon: <BugOutlined />, title: "Диагностика", desc: "Состояние системы, метрики", path: "/admin/diagnostics" },
  { key: "operations", icon: <ThunderboltOutlined />, title: "Operations", desc: "Мониторинг очередей, профилирование", path: "/admin/operations" },
];

export default function Settings() {
  const { colors } = useTheme();
  const navigate = useNavigate();

  return (
    <div style={{ padding: spacing[4], maxWidth: 1200, margin: "0 auto" }}>
      <div style={{ marginBottom: spacing[4] }}>
        <Title level={3} style={{ margin: 0, fontSize: 20, fontWeight: 600, color: colors.text.primary }}>
          <SettingOutlined style={{ marginRight: 8 }} />Центр настроек
        </Title>
        <Text style={{ fontSize: 12, color: colors.text.tertiary }}>Управление платформой, безопасностью и интеграциями</Text>
      </div>

      <Row gutter={[12, 12]}>
        {sections.map(s => (
          <Col span={8} key={s.key}>
            <div style={{ ...cardStyle, padding: spacing[4], cursor: "pointer", transition: "border-color 0.15s" }}
              onClick={() => navigate(s.path)}
              onMouseEnter={e => { e.currentTarget.style.borderColor = colors.brand[400]; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = colors.border; }}>
              <Space>
                <span style={{ fontSize: 20, color: colors.brand[500] }}>{s.icon}</span>
                <div>
                  <Text strong style={{ fontSize: 14, color: colors.text.primary, display: "block" }}>{s.title}</Text>
                  <Text style={{ fontSize: 11, color: colors.text.tertiary }}>{s.desc}</Text>
                </div>
              </Space>
            </div>
          </Col>
        ))}
      </Row>
    </div>
  );
}
