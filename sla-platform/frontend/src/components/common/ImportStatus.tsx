import { Tag, Tooltip } from "antd";

interface ImportStatusProps {
  status: string;
  progress?: number;
}

export default function ImportStatus({ status }: ImportStatusProps) {
  const colorMap: Record<string, string> = {
    completed: "green",
    failed: "red",
    parsing: "processing",
    validating: "processing",
    normalizing: "processing",
    rebuilding: "processing",
    draft: "default",
  };

  return (
    <Tooltip title={`Status: ${status}`}>
      <Tag color={colorMap[status] || "default"}>{status}</Tag>
    </Tooltip>
  );
}
