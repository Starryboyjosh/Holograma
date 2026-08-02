import { Navigate, Route, Routes } from 'react-router-dom';
import { SessionProvider } from './context/SessionContext';
import { AppShell } from './components/AppShell';
import { ScrollToTop } from './components/ScrollToTop';
import { LandingScreen } from './screens/LandingScreen';
import { SettingsScreen } from './screens/SettingsScreen';
import { CameraWidget } from './widgets/CameraWidget';
import { ChatWidget } from './widgets/ChatWidget';
import { TranscriptWidget } from './widgets/TranscriptWidget';

// The main window shares one live session (chat socket, hologram, config, camera)
// across all screens; AppShell renders the nav + the active screen via Outlet.
function ShellLayout() {
  return (
    <SessionProvider>
      <AppShell />
    </SessionProvider>
  );
}

// Thin router. Detachable widget windows render standalone (their own React root,
// their own hooks) and therefore live OUTSIDE the SessionProvider shell.
//
// INICIO/HABLAR/ENTRENAR VISIÓN/INFO. UNEV se fusionaron en una sola landing de
// una página (ver LandingScreen); CONFIGURACIÓN sigue siendo una ruta aparte,
// como en el diseño Figma (nodo 63:36 es un frame independiente, no parte del
// recorrido de las otras cuatro secciones).
export default function App() {
  return (
    <Routes>
      <Route path="/widget/camera" element={<CameraWidget />} />
      <Route path="/widget/chat" element={<ChatWidget />} />
      <Route path="/widget/transcript" element={<TranscriptWidget />} />

      <Route path="/" element={<ShellLayout />}>
        <ScrollToTop />
        <Route index element={<LandingScreen />} />
        <Route path="settings" element={<SettingsScreen />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
