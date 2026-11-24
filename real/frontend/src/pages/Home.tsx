// src/pages/Home.tsx
import React from 'react';
import Hero from './Hero';
import HowItWorks from './HowItWorks';
import WhenPapersAreLost from './WhenPapersAreLost';
import ForOfficialsTeaser from './ForOfficialsTeaser';
import PoweredByGemini from './PoweredByGemini';

export const Home: React.FC = () => {
  return (
    <div>
      {/* 1) Hero */}
      <Hero />

      {/* 2) How it works (bg) */}
      <div className="section-bg">
        <HowItWorks />
      </div>

      {/* 3) When papers are lost (bg-alt) */}
      <div className="section-bg-alt">
        <WhenPapersAreLost />
      </div>

      {/* 4) For officials (bg) */}
      <div className="section-bg">
        <ForOfficialsTeaser />
      </div>

      {/* 5) Powered by Gemini (bg-alt) */}
      <div className="section-bg-alt">
        <PoweredByGemini />
      </div>
    </div>
  );
};

export default Home;
