import { Typography, Tabs, Button, Space, message, Tag } from "antd";
import { ClockCircleOutlined, StarFilled, StarOutlined, PushpinOutlined } from "@ant-design/icons";
import QueueCommandView from "../components/operations/QueueCommandView";
import { useFavorites } from "../contexts/FavoritesContext";
import { useTimeScope } from "../contexts/TimeScopeContext";
import "../design/v1-tokens.css";

const { Title, Text } = Typography;

const QUEUES = [
  "MBR-137-AssetManagement-Veshki",
  "MBR-137-AssetManagement-Plaza",
];

export default function AssetCommandCenter() {
  const { favoriteSet, toggle, setActiveFilter } = useFavorites();
  const { label: scopeLabel } = useTimeScope();
  const allStarred = QUEUES.every(q => favoriteSet.has(q));

  const onStarAll = () => {
    QUEUES.forEach(q => { if (!favoriteSet.has(q)) toggle(q); });
    message.success("Все Asset Management-очереди добавлены в избранное");
  };
  const onApplyFilter = () => {
    setActiveFilter(QUEUES);
    message.info("Платформа сфокусирована на Asset Management");
  };

  return (
    <div className="v1" style={{ background: "var(--v1-bg)", minHeight: "100vh", padding: 24 }}>
      <Title level={3} style={{ margin: 0, color: "var(--v1-text)" }}>
        Asset Management Command Center
      </Title>
      <Text style={{ color: "var(--v1-text-3)" }}>
        Операционная панель по продакшен-очередям Asset Management · Veshki и Plaza.
        Aging-инвентарь, dead queues, ownership-gaps, длинные approval-chain'ы.
        &nbsp;·&nbsp;
        <Tag icon={<ClockCircleOutlined />} color="blue">{scopeLabel}</Tag>
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
          Активировать фильтр на Asset Management
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
