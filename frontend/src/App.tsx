import { Route, Routes } from 'react-router-dom';
import { SessionProvider } from './context/SessionContext';
import { AppShell } from './components/AppShell';
import { HomeScreen } from './screens/HomeScreen';
import { AssistantScreen } from './screens/AssistantScreen';
import { SettingsScreen } from './screens/SettingsScreen';
import { RemoteScreen } from './screens/RemoteScreen';
import { TeachingScreen } from './screens/TeachingScreen';
import { ContentScreen } from './screens/ContentScreen';
import { CameraWidget } from './widgets/CameraWidget';
import { ChatWidget } from './widgets/ChatWidget';
import { TranscriptWidget } from './widgets/TranscriptWidget';
import { ControlsWidget } from './widgets/ControlsWidget';

// The main window shares one live session (chat socket, hologram, config, camera)
// across all five screens; AppShell renders the nav + the active screen via Outlet.
function ShellLayout() {
  return (
    <SessionProvider>
      <AppShell />
    </SessionProvider>
  );
}

// Thin router. Detachable widget windows render standalone (their own React root,
// their own hooks) and therefore live OUTSIDE the SessionProvider shell.
export default function App() {
  return (
    <Routes>
      <Route path="/widget/camera" element={<CameraWidget />} />
      <Route path="/widget/chat" element={<ChatWidget />} />
      <Route path="/widget/transcript" element={<TranscriptWidget />} />
      <Route path="/widget/controls" element={<ControlsWidget />} />

      <Route path="/" element={<ShellLayout />}>
        <Route index element={<HomeScreen />} />
        <Route path="assistant" element={<AssistantScreen />} />
        <Route path="settings" element={<SettingsScreen />} />
        <Route path="content" element={<ContentScreen />} />
        <Route path="remote" element={<RemoteScreen />} />
        <Route path="teaching" element={<TeachingScreen />} />
        <Route path="*" element={<HomeScreen />} />
      </Route>
    </Routes>
  );
}
