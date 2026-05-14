import { useState } from "react";
import { Typography, Upload, Button, Card, message } from "antd";
import { InboxOutlined } from "@ant-design/icons";
import { importsApi } from "../api/imports";
import { useNavigate } from "react-router-dom";
import type { UploadFile } from "antd/es/upload/interface";

const { Dragger } = Upload;

export default function ImportUpload() {
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const navigate = useNavigate();

  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.warning("Please select files");
      return;
    }
    setUploading(true);
    try {
      const formData = new FormData();
      let hasBacklog = false;
      let hasHistory = false;

      fileList.forEach((f) => {
        const file = f.originFileObj as File;
        if (!file) return;
        if (file.name.toLowerCase().includes("backlog")) {
          formData.append("backlog", file);
          hasBacklog = true;
        } else if (file.name.toLowerCase().includes("history")) {
          formData.append("history", file);
          hasHistory = true;
        } else {
          formData.append("backlog", file);
          hasBacklog = true;
        }
      });

      if (!hasBacklog && !hasHistory) {
        message.error("Please upload backlog and/or history CSV files");
        setUploading(false);
        return;
      }

      const resp = await importsApi.create(formData);
      message.success("Import session created");

      const id = (resp.data as any).id;
      if (id && hasBacklog && hasHistory) {
        await importsApi.start(id);
        message.loading({ content: "Pipeline started...", key: "pipeline" });
      }

      navigate("/imports");
    } catch {
      message.error("Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <Typography.Title level={4}>New Import</Typography.Title>
      <Card>
        <Dragger
          multiple
          accept=".csv"
          fileList={fileList}
          onChange={({ fileList }) => setFileList(fileList)}
          beforeUpload={() => false}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p>Click or drag CSV files to upload</p>
          <p>Upload backlog_*.csv and history_*.csv files</p>
        </Dragger>
        <Button
          type="primary"
          onClick={handleUpload}
          loading={uploading}
          disabled={fileList.length === 0}
          style={{ marginTop: 16 }}
        >
          {uploading ? "Uploading..." : "Start Import"}
        </Button>
      </Card>
    </div>
  );
}