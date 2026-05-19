import { Component, type ReactNode, type ErrorInfo } from "react";
import { palette } from "../../design/colors";

interface SafeChartProps {
  children: ReactNode;
  fallback?: ReactNode;
  name?: string;
}

interface SafeChartState {
  hasError: boolean;
  error: Error | null;
}

export class SafeChart extends Component<SafeChartProps, SafeChartState> {
  constructor(props: SafeChartProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): SafeChartState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.warn(`[SafeChart${this.props.name ? ` ${this.props.name}` : ""}]`, error.message, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div style={{ padding: 24, textAlign: "center", color: palette.text.tertiary, fontSize: 13 }}>
          ⚠ Ошибка загрузки графика
        </div>
      );
    }
    return this.props.children;
  }
}
