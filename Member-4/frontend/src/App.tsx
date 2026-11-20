// src/App.tsx
import React from 'react';
import { Routes, Route } from 'react-router-dom';
import TopNav from './components/TopNav';
import Footer from './components/Footer';
import Home from './pages/Home';
import Claim from './pages/Claim';
import Track from './pages/Track';
import Official from './pages/Official';
import Prepare from './pages/Prepare';
import Mesh from './pages/Mesh';
import { OfflineBanner } from './components/OfflineBanner';
import { A11yProvider } from './utils/accessibility';

const App: React.FC = () => {
  return (
    <A11yProvider>
      <div className="app-container" style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <OfflineBanner />
        <TopNav />
        <main style={{ flex: 1 }}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/claim/*" element={<Claim />} />
            <Route path="/track" element={<Track />} />
            <Route path="/official" element={<Official />} />
            <Route path="/prepare" element={<Prepare />} />
            <Route path="/mesh" element={<Mesh />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </A11yProvider>
  );
};

export default App;
