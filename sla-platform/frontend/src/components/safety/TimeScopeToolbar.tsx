import { Segmented, DatePicker, Space, Tag, Tooltip } from "antd";
import { ClockCircleOutlined } from "@ant-design/icons";
import { useState } from "react";
import dayjs, { type Dayjs } from "dayjs";
import { useTimeScope, type ScopePreset } from "../../contexts/TimeScopeContext";

const { RangePicker } = DatePicker;

const OPTIONS = [
  { label: "Всё время", value: "all" as const },
  { label: "24ч",       value: "24h" as const },
  { label: "7д",        value: "7d"  as const },
  { label: "30д",       value: "30d" as const },
  { label: "90д",       value: "90d" as const },
  { label: "Период",    value: "custom" as const },
];

/**
 * Header-bar control for the global TimeScope. Stateless from the
 * caller's POV — just renders the current state and posts updates.
 * No hooks issues: useTimeScope + useState + handler, no conditional
 * returns inside hook block.
 */
export default function TimeScopeToolbar() {
  const { preset, since, until, setPreset, setCustomRange, label } = useTimeScope();
  const [pickerValue, setPickerValue] = useState<[Dayjs | null, Dayjs | null]>(() => {
    if (preset === "custom" && since && until) {
      return [dayjs(since), dayjs(until)];
    }
    return [null, null];
  });

  return (
    <Space size={8} align="center">
      <Tooltip title={`Forensic scope · ${label}`}>
        <Tag icon={<ClockCircleOutlined />} color="blue" style={{ marginRight: 0 }}>
          {label}
        </Tag>
      </Tooltip>
      <Segmented
        size="small"
        value={preset}
        options={OPTIONS}
        onChange={(v) => setPreset(v as ScopePreset)}
      />
      {preset === "custom" && (
        <RangePicker
          size="small"
          showTime={false}
          value={pickerValue}
          onChange={(range) => {
            if (range && range[0] && range[1]) {
              setPickerValue([range[0], range[1]]);
              setCustomRange(
                range[0].toDate().toISOString(),
                range[1].toDate().toISOString(),
              );
            }
          }}
        />
      )}
    </Space>
  );
}
