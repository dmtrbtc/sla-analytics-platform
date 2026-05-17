import { Button, Result } from "antd";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

export default function NotFound() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  return (
    <Result
      status="404"
      title={t("notFound.title")}
      subTitle={t("notFound.subtitle")}
      extra={
        <Button type="primary" onClick={() => navigate("/")}>
          {t("notFound.backToDashboard")}
        </Button>
      }
    />
  );
}
