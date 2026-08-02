import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import { ToastProvider } from './context/ToastContext'

// HashRouter (not BrowserRouter) so deep links like #/widget/camera resolve under
// Tauri's asset protocol, the packaged app, and FastAPI's static serving without
// any server-side rewrite. ToastProvider wraps both the shell and the detachable
// widget windows.
//
// El diseño Holomind-WEB define un solo aspecto, así que ya no hay ThemeProvider:
// el tema claro/oscuro se retiró junto con su toggle.
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ToastProvider>
      <HashRouter>
        <App />
      </HashRouter>
    </ToastProvider>
  </StrictMode>,
)
