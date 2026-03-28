"use client";

import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
}

export class SceneErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="w-full h-full rounded-xl bg-gradient-to-br from-slate-100 to-slate-50 flex items-center justify-center">
            <p className="text-xs text-slate-400">3D view unavailable</p>
          </div>
        )
      );
    }
    return this.props.children;
  }
}
