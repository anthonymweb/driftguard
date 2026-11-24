import { Component } from 'react';

export class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="fatal" role="alert">
          <p className="engraved">CONSOLE ERROR</p>
          <h1>The console hit an unexpected error.</h1>
          <p className="mono">{this.state.error.message}</p>
          <button
            type="button"
            className="secondary-button"
            onClick={() => window.location.reload()}
          >
            Reload
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
