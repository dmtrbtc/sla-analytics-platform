import type { ReactNode } from "react";
import { Space, Button, Tooltip } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import { palette } from "../../design/colors";

interface FilterGroup {
  label?: string;
  content: ReactNode;
}

interface EnterpriseFiltersProps {
  groups: FilterGroup[];
  onReset?: () => void;
  extra?: ReactNode;
  sticky?: boolean;
}

export function EnterpriseFilters({ groups, onReset, extra, sticky }: EnterpriseFiltersProps) {
  return (
    <div
      style={{
        background: palette.white,
        borderBottom: sticky ? `1px solid ${palette.borderLight}` : `1px solid ${palette.borderLight}`,
        padding: "10px 16px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 12,
        flexWrap: "wrap",
        ...(sticky ? { position: "sticky", top: 0, zIndex: 10 } : {}),
      }}
    >
      <Space wrap size={[8, 6]}>
        {groups.map((g, i) => (
          <Space key={i} size={4}>
            {g.label && <span style={{ fontSize: 11, color: palette.text.tertiary, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em" }}>{g.label}</span>}
            {g.content}
          </Space>
        ))}
      </Space>
      <Space size={4}>
        {onReset && (
          <Tooltip title="Сбросить фильтры">
            <Button size="small" icon={<ReloadOutlined />} onClick={onReset} />
          </Tooltip>
        )}
        {extra}
      </Space>
    </div>
  );
}
