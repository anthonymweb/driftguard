import React from 'react';
import { createRoot } from 'react-dom/client';
import '@fontsource-variable/chivo';
import '@fontsource-variable/chivo-mono';
import './styles/index.css';
import App from './App.jsx';
import { ErrorBoundary } from './components/ErrorBoundary.jsx';

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
);
