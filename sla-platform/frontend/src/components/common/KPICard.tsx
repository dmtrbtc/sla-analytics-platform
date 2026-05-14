import { Card, Statistic } from "antd";
import { ArrowUpOutlined, ArrowDownOutlined } from "@ant-design/icons";

interface KPICardProps {
  title: string;
  value: number | string;
  prefix?: string;
  trend?: number;
  color?: string;
}

export default function KPICard({ title, value, prefix, trend, color }: KPICardProps) {
  return (
    <Card>
      <Statistic
        title={title}
        value={value}
        prefix={prefix}
        valueStyle={{ color: color || "#000" }}
        suffix={
          trend !== undefined ? (
            <span style={{ fontSize: 14, color: trend >= 0 ? "#52c41a" : "#ff4d4f" }}>
              {trend >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
              {Math.abs(trend)}%
            </span>
          ) : null
        }
      />
    </Card>
  );
}
