import { Component, type ErrorInfo, type ReactNode } from 'react';

type Props = { children: ReactNode };
type State = { message?: string };

function reportError(message: string, componentStack: string) {
  window.durabilityManagerAction?.(JSON.stringify({ type: 'clientError', message, componentStack }));
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = {};

  static getDerivedStateFromError(error: unknown): State {
    return { message: error instanceof Error ? error.message : String(error) };
  }

  componentDidCatch(error: unknown, info: ErrorInfo) {
    reportError(error instanceof Error ? error.message : String(error), info.componentStack ?? '');
  }

  render() {
    if (this.state.message) {
      return <main className="panel-error" role="alert">
        <p>DURABILITY MANAGER</p>
        <h1>面板数据异常</h1>
        <span>{this.state.message}</span>
        <button onClick={() => window.durabilityManagerAction?.(JSON.stringify({ type: 'close' }))} type="button">关闭面板</button>
      </main>;
    }
    return this.props.children;
  }
}
