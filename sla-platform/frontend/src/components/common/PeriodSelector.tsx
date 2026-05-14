import { DatePicker, Space } from "antd";
import dayjs from "dayjs";

const { RangePicker } = DatePicker;

interface PeriodSelectorProps {
  onChange?: (dates: [dayjs.Dayjs, dayjs.Dayjs] | null) => void;
}

export default function PeriodSelector({ onChange }: PeriodSelectorProps) {
  return (
    <Space>
      <RangePicker onChange={(dates) => onChange?.(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)} />
    </Space>
  );
}
