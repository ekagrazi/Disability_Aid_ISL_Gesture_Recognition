import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Cam from './pages/Cam';
import Video from './pages/Video';
import Signs from './pages/Signs';
import Help from './pages/Help';
import Settings from './pages/Settings';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Cam />} />
          <Route path="video" element={<Video />} />
          <Route path="signs" element={<Signs />} />
          <Route path="help" element={<Help />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
