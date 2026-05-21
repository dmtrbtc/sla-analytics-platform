import { Component, type ErrorInfo, type ReactNode } from "react";
import { Result, Button, Typography } from "antd";
import { ReloadOutlined } from "@ant-design/icons";

const { Paragraph, Text } = Typography;

interface Props {
  /** What to call the failing region in the fallback ("страница", "виджет", "график", …) */
  label?: string;
  /** Custom fallback. If omitted, an Ant Result is rendered. */
  fallback?: (error: Error, reset: () => void) => ReactNode;
  /** If true, never auto-reset on prop change. Default: false. */
  noAutoReset?: boolean;
  /** Reset key: when this changes, the boundary tries to remount the subtree. */
  resetKey?: unknown;
  children: ReactNode;
}

interface State {
  error: Error | null;
  /** Counter forces remount of children after reset() is called. */
  resetCount: number;
}

/**
 * Runtime error boundary — catches any synchronous render error in the
 * subtree (including hook-order violations, undefined-access crashes,
 * thrown promises misuse) and displays a contained fallback INSTEAD OF
 * white-screening the whole app.
 *
 * Usage (one per major widget OR one per route):
 *
 *   <RuntimeErrorBoundary label="график">
 *     <ReactECharts option={chartOption} />
 *   </RuntimeErrorBoundary>
 *
 * Note: React's `componentDidCatch` only fires on errors thrown during
 * render. Errors inside event handlers or async callbacks still bubble
 * to window.onerror and need their own try/catch — that's a React
 * limitation, not this boundary's.
 */
export default class RuntimeErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { error: null, resetCount: 0 };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // eslint-disable-next-line no-console
    console.error(
      `[RuntimeErrorBoundary${this.props.label ? " " + this.props.label : ""}]`,
      error,
      info.componentStack,
    );
  }

  componentDidUpdate(prevProps: Props): void {
    // When resetKey changes (e.g. user navigated away and back, or
    // filter changed), drop the cached error so the boundary tries
    // to render its children again.
    if (
      !this.props.noAutoReset
      && this.state.error
      && prevProps.resetKey !== this.props.resetKey
    ) {
      this.reset();
    }
  }

  reset = (): void => {
    this.setState((s) => ({ error: null, resetCount: s.resetCount + 1 }));
  };

  render(): ReactNode {
    const { error, resetCount } = this.state;
    if (error) {
      if (this.props.fallback) return this.props.fallback(error, this.reset);
      const label = this.props.label || "элемент";
      return (
        <Result
          status="error"
          title={`Не удалось отобразить ${label}`}
          subTitle={
            <span>
              Внутренняя ошибка интерфейса. Это не повлияло на остальную часть платформы.
            </span>
          }
          extra={
            <Button type="primary" icon={<ReloadOutlined />} onClick={this.reset}>
              Перезагрузить блок
            </Button>
          }
        >
          <Paragraph>
            <Text type="secondary" style={{ fontFamily: "monospace", fontSize: 12 }}>
              {error.name}: {error.message}
            </Text>
          </Paragraph>
        </Result>
      );
    }
    // Force remount of children when reset() was called so they re-mount
    // cleanly instead of re-using the broken instance.
    return <span key={resetCount} style={{ display: "contents" }}>{this.props.children}</span>;
  }
}
