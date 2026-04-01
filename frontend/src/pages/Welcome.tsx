import React, { Suspense, lazy } from 'react'

const SiraMap = lazy(() => import('../components/map/SiraMap'))

const Loader: React.FC = () => (
  <div style={{
    width: '100vw', height: '100vh', background: '#070e1a',
    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
    gap: 20,
  }}>
    <div style={{
      width: 56, height: 56, borderRadius: 14,
      background: 'linear-gradient(135deg,#00ffcc,#0070ff)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontWeight: 900, fontSize: 24, color: '#000',
    }}>S</div>
    <p style={{ color: '#00ffcc', fontWeight: 800, fontSize: 22, letterSpacing: 4, margin: 0 }}>SIRA</p>
    <p style={{ color: '#4a6080', fontSize: 13, margin: 0 }}>Loading African Infrastructure Map…</p>
    <div style={{
      width: 160, height: 3, background: '#0f1a2b', borderRadius: 2, overflow: 'hidden',
    }}>
      <div style={{
        width: '60%', height: '100%', background: 'linear-gradient(90deg,#00ffcc,#0070ff)',
        borderRadius: 2, animation: 'sira-progress 1.4s ease-in-out infinite',
      }} />
    </div>
    <style>{`
      @keyframes sira-progress {
        0%   { transform: translateX(-100%); }
        100% { transform: translateX(300%); }
      }
    `}</style>
  </div>
)

const Welcome: React.FC = () => (
  <div style={{ width: '100vw', height: '100vh', overflow: 'hidden' }}>
    <Suspense fallback={<Loader />}>
      <SiraMap />
    </Suspense>
  </div>
)

export default Welcome
