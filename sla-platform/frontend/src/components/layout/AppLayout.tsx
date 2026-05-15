import { Outlet } from "react-router-dom";
import { Layout } from "antd";
import Sidebar from "./Sidebar";
import Header from "./Header";
import WebSocketWrapper from "../common/WebSocketWrapper";

const { Content } = Layout;

export default function AppLayout() {
  return (
    <Layout style={{ minHeight: "100vh" }}>
      <WebSocketWrapper />
      <Sidebar />
      <Layout>
        <Header />
        <Content style={{ margin: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
