/**
 * DeepTrust Frontend Entry Point
 * ==============================
 * This module initializes the React application and mounts it to the DOM.
 * 
 * StrictMode: Enabled to identify potential side-effect issues during development.
 * createRoot: Utilizes React 18 Concurrent Rendering features.
 */

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './index.css'

// Target the primary root element defined in the index.html template
const container = document.getElementById('root');

if (container) {
  const root = createRoot(container);
  
  root.render(
    <StrictMode>
      {/* Root Application Component */}
      <App />
    </StrictMode>,
  );
} else {
  // Critical error handling if the DOM structure is missing expected hooks
  console.error('DeepTrust Launch Failure: Root container not found in the document.');
}
