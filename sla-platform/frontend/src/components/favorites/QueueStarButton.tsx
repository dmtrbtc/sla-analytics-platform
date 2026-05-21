import { StarFilled, StarOutlined } from "@ant-design/icons";
import { Tooltip } from "antd";
import { useFavorites } from "../../contexts/FavoritesContext";

interface Props {
  queue: string;
  size?: number;
  inline?: boolean;
  className?: string;
}

/**
 * Star/unstar a queue. Optimistic — UI flips instantly, errors roll back.
 * Drop in next to any queue name to make it favoritable.
 */
export default function QueueStarButton({ queue, size = 14, inline = false, className }: Props) {
  const { isStarred, toggle } = useFavorites();
  const starred = isStarred(queue);
  const icon = starred
    ? <StarFilled style={{ color: "#f5c518", fontSize: size }} />
    : <StarOutlined style={{ color: "#a8a8a8", fontSize: size }} />;
  return (
    <Tooltip title={starred ? "Убрать из избранного" : "Добавить в избранное"}>
      <span
        role="button"
        tabIndex={0}
        aria-pressed={starred}
        onClick={(e) => { e.stopPropagation(); toggle(queue); }}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(queue); } }}
        className={className}
        style={{
          cursor: "pointer",
          display: inline ? "inline-flex" : "inline-flex",
          alignItems: "center",
          padding: 2,
          lineHeight: 1,
        }}
      >
        {icon}
      </span>
    </Tooltip>
  );
}
