import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Typography, Card, Form, Input, Button, message, Alert } from "antd";
import { MailOutlined, LockOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { authApi } from "../api/auth";
import { useAuthStore } from "../stores/authStore";

export default function Login() {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);

  const handleSubmit = async (values: { email: string; password: string }) => {
    setLoading(true);
    setError(null);

    try {
      const resp = await authApi.login(values.email, values.password);
      const { access_token, refresh_token } = resp.data;

      localStorage.setItem("access_token", access_token);
      localStorage.setItem("refresh_token", refresh_token);

      const meResp = await authApi.me();
      const user = meResp.data;

      setAuth(access_token, refresh_token, user);
      message.success(t("auth.welcomeBack"));
      navigate("/", { replace: true });
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(detail || t("auth.invalidCredentials"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: "100vh",
        background: "#f0f2f5",
      }}
    >
      <Card
        title={
          <Typography.Title level={3} style={{ margin: 0, textAlign: "center" }}>
            {t("app.title")}
          </Typography.Title>
        }
        style={{ width: 400 }}
      >
        {error && (
          <Alert
            message={error}
            type="error"
            showIcon
            closable
            onClose={() => setError(null)}
            style={{ marginBottom: 16 }}
          />
        )}
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          autoComplete="off"
        >
          <Form.Item
            name="email"
            label={t("auth.emailLogin")}
            rules={[
              { required: true, message: t("auth.pleaseEnterEmail") },
            ]}
          >
            <Input prefix={<MailOutlined />} placeholder="admin" size="large" />
          </Form.Item>
          <Form.Item
            name="password"
            label={t("auth.password")}
            rules={[{ required: true, message: t("auth.pleaseEnterPassword") }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="••••••" size="large" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading} size="large">
            {t("auth.signIn")}
          </Button>
        </Form>
        <Typography.Text type="secondary" style={{ display: "block", textAlign: "center", marginTop: 12, fontSize: 12 }}>
          {t("auth.defaultCredentials")}
        </Typography.Text>
      </Card>
    </div>
  );
}
