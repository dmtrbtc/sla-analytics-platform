import { Tag } from "antd";

const statusColors: Record<string, string> = {
  completed: "green",
  failed: "red",
  parsing: "blue",
  validating: "orange",
  draft: "default",
};

interface StatusTagProps {
  status: string;
}

export default function StatusTag({ status }: StatusTagProps) {
  return (
    <Tag color={statusColors[status] || "default"}>
      {status.toUpperCase()}
    </Tag>
  );
}
