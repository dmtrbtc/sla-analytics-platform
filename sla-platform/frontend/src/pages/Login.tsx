import { Typography, Card, Form, Input, Button, message } from "antd";

export default function Login() {
  const [form] = Form.useForm();

  const handleSubmit = () => {
    message.info("Auth not implemented yet");
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
      <Card title="SLA Analytics Platform" style={{ width: 400 }}>
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="email" label="Email" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="password" label="Password" rules={[{ required: true }]}>
            <Input.Password />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>
            Sign In
          </Button>
        </Form>
      </Card>
    </div>
  );
}
