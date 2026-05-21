import { Typography, Tabs, Button, Space, message } from "antd";
import { StarFilled, StarOutlined, PushpinOutlined } from "@ant-design/icons";
import QueueCommandView from "../components/operations/QueueCommandView";
import { useFavorites } from "../contexts/FavoritesContext";
import "../design/v1-tokens.css";

const { Title, Text } = Typography;

const QUEUES = [
  "MBR-137-Workplace-Veshki",
  "MBR-137-Workplace-Plaza",
];

export default function WorkplaceCommandCenter() {
  const { favoriteSet, toggle, setActiveFilter } = useFavorites();
  const allStarred = QUEUES.every(q => favoriteSet.has(q));

  // No conditional hooks, so this is safe — just plain handlers.
  const onStarAll = () => {
    QUEUES.forEach(q => { if (!favoriteSet.has(q)) toggle(q); });
    message.success("Все Workplace-очереди добавлены в избранное");
  };
  const onApplyFilter = () => {
    setActiveFilter(QUEUES);
    message.info("Платформа сфокусирована на Workplace");
  };

  return (
    <div className="v1" style={{ background: "var(--v1-bg)", minHeight: "100vh", padding: 24 }}>
      <Title level={3} style={{ margin: 0, color: "var(--v1-text)" }}>
        Workplace Command Center
      </Title>
      <Text style={{ color: "var(--v1-text-3)" }}>
        Операционная панель по продакшен-очередям Workplace · Veshki и Plaza.
        Поиск перегруженных инженеров, aging-тикетов, bounces и SLA-давления.
      </Text>

      <Space style={{ marginTop: 12, marginBottom: 18 }}>
        <Button
          icon={allStarred ? <StarFilled style={{ color: "#f5c518" }} /> : <StarOutlined />}
          onClick={onStarAll}
          disabled={allStarred}
        >
          {allStarred ? "Уже в избранном" : "Добавить обе очереди в избранное"}
        </Button>
        <Button type="primary" icon={<PushpinOutlined />} onClick={onApplyFilter}>
          Активировать фильтр на Workplace
        </Button>
      </Space>

      <Tabs
        items={QUEUES.map(q => ({
          key: q,
          label: q.replace("MBR-137-", ""),
          children: <QueueCommandView queueName={q} />,
        }))}
      />
    </div>
  );
}
