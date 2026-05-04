import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="flex min-h-screen items-center justify-center bg-[var(--bg)] px-4">
            <div className="max-w-md rounded-[26px] border border-[color:var(--panel-border)] bg-[color:var(--panel)] p-6 text-center shadow-[0_24px_60px_rgba(148,163,184,0.16)]">
              <p className="text-[0.72rem] font-semibold uppercase tracking-[0.28em] text-[color:var(--text-soft)]">
                Error
              </p>
              <h2 className="mt-3 text-2xl font-medium text-[color:var(--text-h)]">
                Algo salió mal
              </h2>
              <p className="mt-2 text-sm text-[color:var(--text)]">
                {this.state.error?.message ?? "Error inesperado."}
              </p>
              <button
                type="button"
                onClick={() => window.location.reload()}
                className="mt-5 rounded-xl bg-[color:var(--text-h)] px-5 py-2.5 text-sm font-medium text-white transition hover:opacity-85"
              >
                Recargar página
              </button>
            </div>
          </div>
        )
      );
    }

    return this.props.children;
  }
}
