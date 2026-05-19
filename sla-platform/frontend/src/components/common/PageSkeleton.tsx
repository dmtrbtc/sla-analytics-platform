import { Skeleton, Row, Col } from "antd";
import { palette } from "../../design/colors";
import { cardStyle } from "../../design/tokens";

interface PageSkeletonProps {
  kpiCount?: number;
  chartHeight?: number;
}

export function PageSkeleton({ kpiCount = 6, chartHeight = 260 }: PageSkeletonProps) {
  return (
    <div style={{ padding: "24px 0" }}>
      <Row gutter={[12, 12]} style={{ marginBottom: 20 }}>
        {Array.from({ length: kpiCount }).map((_, i) => (
          <Col xs={12} sm={8} lg={4} key={i}>
            <div style={{ ...cardStyle, padding: 16 }}>
              <Skeleton active paragraph={false} title={{ width: "60%" }} />
              <Skeleton active paragraph={false} title={{ width: "40%" }} style={{ marginTop: 8 }} />
            </div>
          </Col>
        ))}
      </Row>
      <div style={{ ...cardStyle, padding: 20, marginBottom: 12 }}>
        <Skeleton active paragraph={{ rows: 1 }} title={{ width: "30%" }} />
        <div style={{ height: chartHeight, background: palette.borderLight, borderRadius: 6, marginTop: 12 }} />
      </div>
      <Row gutter={[12, 12]}>
        {Array.from({ length: 2 }).map((_, i) => (
          <Col xs={24} lg={12} key={i}>
            <div style={{ ...cardStyle, padding: 16 }}>
              <Skeleton active paragraph={{ rows: 4 }} title={{ width: "40%" }} />
            </div>
          </Col>
        ))}
      </Row>
    </div>
  );
}
