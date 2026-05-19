import { Switch, Tooltip, Space, Tag } from "antd";
import { BulbOutlined } from "@ant-design/icons";
import { useDemoMode } from "../../stores/demoMode";
import { palette } from "../../design/colors";

export function DemoModeToggle() {
  const { enabled, toggle } = useDemoMode();
  return (
    <Tooltip title={enabled ? "Режим демо — отключить" : "Включить демо-режим"}>
      <Space size={4}>
        <BulbOutlined style={{ color: enabled ? palette.accent.amber : palette.text.tertiary, fontSize: 14 }} />
        <Switch
          size="small"
          checked={enabled}
          onChange={toggle}
          style={{ background: enabled ? palette.accent.amber : undefined }}
        />
        {enabled && <Tag color="gold" style={{ fontSize: 10, lineHeight: "16px", margin: 0 }}>DEMO</Tag>}
      </Space>
    </Tooltip>
  );
}
