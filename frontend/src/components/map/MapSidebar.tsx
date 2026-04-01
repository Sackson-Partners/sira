import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Map as LeafletMap } from 'leaflet'
import { REGIONS } from './data/infrastructure'

interface LayerState {
  vessels: boolean; ports: boolean; corridors: boolean; railways: boolean;
  gasStations: boolean; mining: boolean; oilGas: boolean; energy: boolean; trucks: boolean;
}

interface Props {
  mapRef: React.MutableRefObject<LeafletMap | null>
  layers: LayerState
  onToggleLayer: (key: keyof LayerState) => void
}

const ALERTS = [
  '🚢 MSC Abidjan entered Port of Abidjan',
  '⛽ Fuel alert: Lagos corridor low supply',
  '⛏️ Kibali Gold — shipment departure',
  '🚢 FPSO Atlantic — production update',
  '🚂 SGR Mombasa — cargo arrived Nairobi',
  '🏗️ Durban port: 35 vessels in queue',
  '🛢️ Bonga Deepwater — output 225k bpd',
  '⚡ Lake Turkana Wind — 310 MW online',
]

const LAYERS: { key: keyof LayerState; label: string; color: string; icon: string }[] = [
  { key: 'vessels',    label: 'Vessels',     color: '#00ffcc', icon: '🚢' },
  { key: 'ports',      label: 'Ports',       color: '#00b4ff', icon: '🏗️' },
  { key: 'corridors',  label: 'Corridors',   color: '#f59e0b', icon: '🚛' },
  { key: 'railways',   label: 'Railways',    color: '#a855f7', icon: '🚂' },
  { key: 'gasStations',label: 'Gas Stations',color: '#fef08a', icon: '⛽' },
  { key: 'mining',     label: 'Mining',      color: '#fbbf24', icon: '⛏️' },
  { key: 'oilGas',     label: 'Oil & Gas',   color: '#f43f5e', icon: '🛢️' },
  { key: 'energy',     label: 'Energy',      color: '#fb923c', icon: '⚡' },
  { key: 'trucks',     label: 'Trucks',      color: '#f97316', icon: '🚛' },
]

const MapSidebar: React.FC<Props> = ({ mapRef, layers, onToggleLayer }) => {
  const navigate = useNavigate()
  const [alertIdx, setAlertIdx] = useState(0)
  const [activeRegion, setActiveRegion] = useState<string | null>(null)
  const alertTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    alertTimer.current = setInterval(() => {
      setAlertIdx(i => (i + 1) % ALERTS.length)
    }, 4000)
    return () => {
      if (alertTimer.current) clearInterval(alertTimer.current)
    }
  }, [])

  const flyTo = (region: string) => {
    const r = REGIONS[region as keyof typeof REGIONS]
    if (r && mapRef.current) {
      mapRef.current.flyTo(r.center, r.zoom, { duration: 1.4 })
    }
    setActiveRegion(region)
  }

  return (
    <div style={{
      position: 'absolute', top: 0, left: 0, bottom: 0, zIndex: 1100,
      width: 272, background: '#070e1a',
      borderRight: '1px solid rgba(0,255,204,0.12)',
      display: 'flex', flexDirection: 'column',
      fontFamily: "'Inter', system-ui, sans-serif",
      overflowY: 'auto',
    }}>
      {/* Logo */}
      <div style={{ padding: '20px 20px 14px', borderBottom: '1px solid rgba(0,255,204,0.1)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: 'linear-gradient(135deg,#00ffcc,#0070ff)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontWeight: 900, fontSize: 14, color: '#000',
          }}>S</div>
          <span style={{ color: '#00ffcc', fontWeight: 800, fontSize: 20, letterSpacing: 3 }}>SIRA</span>
        </div>
        <p style={{ color: '#4a6080', fontSize: 11, margin: 0, letterSpacing: 0.5 }}>
          African Infrastructure Intelligence
        </p>
      </div>

      {/* Live stats */}
      <div style={{ padding: '14px 20px', borderBottom: '1px solid rgba(0,255,204,0.08)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
          <div style={{
            width: 7, height: 7, borderRadius: '50%', background: '#00ffcc',
            boxShadow: '0 0 6px #00ffcc', animation: 'pulse 2s infinite',
          }} />
          <span style={{ color: '#64748b', fontSize: 10, letterSpacing: 1, textTransform: 'uppercase' }}>Live Data</span>
        </div>
        {[
          ['🚢', '13', 'Vessels Tracked'],
          ['🏗️', '15', 'Ports Monitored'],
          ['🚛', '8',  'Active Corridors'],
          ['⛏️', '10', 'Mining Sites'],
          ['⚡', '10', 'Energy Sites'],
          ['🛢️', '10', 'Oil & Gas Fields'],
        ].map(([icon, count, label]) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ fontSize: 12, color: '#64748b' }}>{icon} {label}</span>
            <span style={{ fontSize: 13, fontWeight: 700, color: '#00ffcc', fontVariantNumeric: 'tabular-nums' }}>{count}</span>
          </div>
        ))}
      </div>

      {/* Region navigator */}
      <div style={{ padding: '14px 20px', borderBottom: '1px solid rgba(0,255,204,0.08)' }}>
        <p style={{ color: '#4a6080', fontSize: 10, letterSpacing: 1, textTransform: 'uppercase', margin: '0 0 8px' }}>
          Region
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
          {[
            ['westAfrica',    'West Africa'],
            ['eastAfrica',    'East Africa'],
            ['southernAfrica','Southern Africa'],
            ['fullAfrica',    'Full Africa'],
          ].map(([key, label]) => (
            <button
              key={key}
              onClick={() => flyTo(key)}
              style={{
                background: activeRegion === key ? 'rgba(0,255,204,0.15)' : 'rgba(255,255,255,0.03)',
                border: `1px solid ${activeRegion === key ? 'rgba(0,255,204,0.5)' : 'rgba(255,255,255,0.07)'}`,
                borderRadius: 6, padding: '6px 8px',
                color: activeRegion === key ? '#00ffcc' : '#64748b',
                fontSize: 11, cursor: 'pointer', textAlign: 'center',
                transition: 'all 0.15s',
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Layer toggles */}
      <div style={{ padding: '14px 20px', borderBottom: '1px solid rgba(0,255,204,0.08)', flex: 1 }}>
        <p style={{ color: '#4a6080', fontSize: 10, letterSpacing: 1, textTransform: 'uppercase', margin: '0 0 10px' }}>
          Layers
        </p>
        {LAYERS.map(({ key, label, color, icon }) => (
          <div key={key}
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8, cursor: 'pointer' }}
            onClick={() => onToggleLayer(key)}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: layers[key] ? color : '#1e2a38', boxShadow: layers[key] ? `0 0 5px ${color}` : 'none', transition: 'all 0.2s' }} />
              <span style={{ fontSize: 12, color: layers[key] ? '#cbd5e1' : '#4a5568' }}>{icon} {label}</span>
            </div>
            {/* Toggle pill */}
            <div style={{
              width: 34, height: 18, borderRadius: 9,
              background: layers[key] ? color : '#1e2a38',
              border: `1px solid ${layers[key] ? color : '#2d3748'}`,
              position: 'relative', transition: 'background 0.2s',
            }}>
              <div style={{
                position: 'absolute', top: 2,
                left: layers[key] ? 16 : 2,
                width: 12, height: 12, borderRadius: '50%',
                background: layers[key] ? '#000' : '#4a5568',
                transition: 'left 0.2s',
              }} />
            </div>
          </div>
        ))}
      </div>

      {/* Alerts feed */}
      <div style={{ padding: '14px 20px', borderBottom: '1px solid rgba(0,255,204,0.08)' }}>
        <p style={{ color: '#4a6080', fontSize: 10, letterSpacing: 1, textTransform: 'uppercase', margin: '0 0 8px' }}>
          Live Alerts
        </p>
        <div style={{
          background: 'rgba(0,255,204,0.04)', borderRadius: 6,
          border: '1px solid rgba(0,255,204,0.1)', padding: '8px 10px',
          minHeight: 38,
        }}>
          <p style={{ color: '#94a3b8', fontSize: 11, margin: 0, lineHeight: 1.5, transition: 'opacity 0.3s' }}>
            {ALERTS[(alertIdx) % ALERTS.length]}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 4, marginTop: 6 }}>
          {ALERTS.slice(0, 5).map((_, i) => (
            <div key={i} style={{
              width: i === alertIdx % 5 ? 16 : 4, height: 3, borderRadius: 2,
              background: i === alertIdx % 5 ? '#00ffcc' : '#1e2a38',
              transition: 'all 0.3s',
            }} />
          ))}
        </div>
      </div>

      {/* CTA */}
      <div style={{ padding: '16px 20px' }}>
        <button
          onClick={() => navigate('/login')}
          style={{
            width: '100%', padding: '11px 0', borderRadius: 8, border: 'none',
            background: 'linear-gradient(90deg,#00ffcc,#0070ff)',
            color: '#000', fontWeight: 700, fontSize: 13, cursor: 'pointer',
            letterSpacing: 0.3, transition: 'opacity 0.2s',
          }}
          onMouseEnter={e => (e.currentTarget.style.opacity = '0.85')}
          onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
        >
          Login to Access Full Platform
        </button>
        <p style={{ color: '#2d3748', fontSize: 10, textAlign: 'center', marginTop: 8 }}>
          Real-time tracking · AI intelligence · Full Africa coverage
        </p>
      </div>
    </div>
  )
}

export default MapSidebar
