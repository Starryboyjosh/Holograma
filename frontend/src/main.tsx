import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import { ThemeProvider } from './context/ThemeContext'
import { ToastProvider } from './context/ToastContext'

// HashRouter (not BrowserRouter) so deep links like #/widget/camera resolve under
// Tauri's asset protocol, the packaged app, and FastAPI's static serving without
// any server-side rewrite. ThemeProvider/ToastProvider wrap both the shell and
// the detachable widget windows.
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <ToastProvider>
        <HashRouter>
          <App />
        </HashRouter>
      </ToastProvider>
    </ThemeProvider>
  </StrictMode>,
)
