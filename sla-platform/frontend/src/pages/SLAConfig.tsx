import { Typography } from "antd";
import { useTranslation } from "react-i18next";

export default function SLAConfig() {
  const { t } = useTranslation();
  return (
    <div>
      <Typography.Title level={4}>{t("slaConfig.title")}</Typography.Title>
      <Typography.Text type="secondary">{t("slaConfig.description")}</Typography.Text>
    </div>
  );
}
