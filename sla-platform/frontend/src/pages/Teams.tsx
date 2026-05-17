import { Typography } from "antd";
import { useTranslation } from "react-i18next";

export default function Teams() {
  const { t } = useTranslation();
  return (
    <div>
      <Typography.Title level={4}>{t("teams.title")}</Typography.Title>
      <Typography.Text type="secondary">{t("teams.description")}</Typography.Text>
    </div>
  );
}
