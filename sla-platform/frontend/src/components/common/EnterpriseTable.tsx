import type { ReactNode } from "react";
import { Table } from "antd";
import type { ColumnsType, TablePaginationConfig } from "antd/es/table";
import { palette } from "../../design/colors";
import { typography } from "../../design/typography";
import { tableTheme } from "../../design/tableTheme";
import { radius } from "../../design/spacing";

interface EnterpriseTableProps<T> {
  columns: ColumnsType<T>;
  dataSource: T[];
  rowKey: string | ((r: T) => string);
  loading?: boolean;
  pagination?: false | TablePaginationConfig;
  scroll?: { y?: number; x?: number };
  emptyText?: string;
  size?: "small" | "middle";
  onRow?: (r: T) => { onClick?: () => void; style?: React.CSSProperties };
}

export function EnterpriseTable<T extends Record<string, any>>({
  columns,
  dataSource,
  rowKey,
  loading,
  pagination = false,
  scroll,
  emptyText,
  size = "small",
  onRow,
}: EnterpriseTableProps<T>) {
  return (
    <Table<T>
      columns={columns}
      dataSource={dataSource}
      rowKey={rowKey}
      loading={loading}
      pagination={pagination}
      scroll={scroll}
      size={size}
      locale={{ emptyText: emptyText || "Нет данных" }}
      onRow={onRow}
      style={{ borderRadius: radius.md, overflow: "hidden" }}
      rowHoverable
    />
  );
}
