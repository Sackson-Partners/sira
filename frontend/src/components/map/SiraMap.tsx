import React, { useState, useEffect, useRef, useCallback } from 'react'
import {
  MapContainer, TileLayer, CircleMarker, Polyline, Popup, useMap,
} from 'react-leaflet'
import { Map as LeafletMap } from 'leaflet'
import 'leaflet/dist/leaflet.css'

import {
  coastalPorts, corridors, railways, trucks, gasStations,
  miningSites, oilGasSites, energySites, REGIONS,
} from './data/infrastructure'
import { useVesselMovement } from './hooks/useVesselMovement'
import MapSidebar from './MapSidebar'
import MapLegend from './MapLegend'

// ── Vessel colour map ─────────────────────────────────────────────────────────
const VESSEL_COLORS: Record<string, string> = {
  container: '#00ffcc',
  tanker:    '#ff6b35',
  bulk:      '#fbbf24',
  cargo:     '#a78bfa',
  offshore:  '#f43f5e',
  fpso:      '#fb923c',
}

interface LayerState {
  vessels: boolean; ports: boolean; corridors: boolean; railways: boolean;
  gasStations: boolean; mining: boolean; oilGas: boolean; energy: boolean; trucks: boolean;
}

// ── Captures the Leaflet map instance from inside MapContainer ────────────────
function MapRefCapture({ mapRef }: { mapRef: React.MutableRefObject<LeafletMap | null> }) {
  const map = useMap()
  useEffect(() => { mapRef.current = map }, [map, mapRef])
  return null
}

// ── Top bar (search + region pills) ──────────────────────────────────────────
function TopBar({ mapRef, activeRegion, setActiveRegion }: {
  mapRef: React.MutableRefObject<LeafletMap | null>
  activeRegion: string | null
  setActiveRegion: (r: string) => void
}) {
  const flyTo = (key: string) => {
    const r = REGIONS[key as keyof typeof REGIONS]
    if (r && mapRef.current) {
      mapRef.current.flyTo(r.center, r.zoom, { duration: 1.4 })
    }
    setActiveRegion(key)
  }

  return (
    <div style={{
      position: 'absolute', top: 12, left: 290, right: 12, zIndex: 1050,
      display: 'flex', alignItems: 'center', gap: 8,
    }}>
      {/* Search bar */}
      <div style={{ flex: 1, maxWidth: 420 }}>
        <input
          style={{
            width: '100%', boxSizing: 'border-box',
            background: 'rgba(7,14,26,0.9)', border: '1px solid rgba(0,255,204,0.25)',
            borderRadius: 8, padding: '9px 16px', color: '#e2e8f0', fontSize: 13,
            outline: 'none', backdropFilter: 'blur(8px)',
          }}
          placeholder="🔍  Search ports, vessels, corridors, mines..."
          onFocus={e => {
            e.target.placeholder = 'Login to search the full platform'
            e.target.style.borderColor = 'rgba(0,255,204,0.5)'
          }}
          onBlur={e => {
            e.target.placeholder = '🔍  Search ports, vessels, corridors, mines...'
            e.target.style.borderColor = 'rgba(0,255,204,0.25)'
          }}
        />
      </div>

      {/* Region pills */}
      {[
        ['westAfrica', 'West Africa'],
        ['eastAfrica', 'East Africa'],
        ['southernAfrica', 'S. Africa'],
        ['fullAfrica', 'Full Africa'],
      ].map(([key, label]) => (
        <button
          key={key}
          onClick={() => flyTo(key)}
          style={{
            background: activeRegion === key ? 'rgba(0,255,204,0.2)' : 'rgba(7,14,26,0.88)',
            border: `1px solid ${activeRegion === key ? 'rgba(0,255,204,0.6)' : 'rgba(255,255,255,0.1)'}`,
            borderRadius: 20, padding: '7px 14px', color: activeRegion === key ? '#00ffcc' : '#94a3b8',
            fontSize: 12, cursor: 'pointer', whiteSpace: 'nowrap',
            backdropFilter: 'blur(8px)', transition: 'all 0.15s',
          }}
        >
          {label}
        </button>
      ))}

      {/* Live indicator */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6,
        background: 'rgba(7,14,26,0.88)', border: '1px solid rgba(0,255,204,0.2)',
        borderRadius: 20, padding: '7px 12px', backdropFilter: 'blur(8px)',
      }}>
        <div style={{
          width: 7, height: 7, borderRadius: '50%', background: '#00ffcc',
          boxShadow: '0 0 6px #00ffcc',
        }} />
        <span style={{ color: '#00ffcc', fontSize: 11, fontWeight: 700, letterSpacing: 1 }}>LIVE</span>
      </div>
    </div>
  )
}

// ── Popup helpers ─────────────────────────────────────────────────────────────
const popupOpts = { closeButton: false, className: 'sira-popup' }

const Row: React.FC<{ label: string; value: React.ReactNode }> = ({ label, value }) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 4 }}>
    <span style={{ color: '#64748b', fontSize: 11 }}>{label}</span>
    <span style={{ color: '#e2e8f0', fontSize: 11, fontWeight: 600 }}>{value}</span>
  </div>
)

const LoginGate: React.FC = () => (
  <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid rgba(0,255,204,0.1)' }}>
    <span style={{ color: '#4a6080', fontSize: 10 }}>🔒 Login to access full details</span>
  </div>
)

// ── Main component ────────────────────────────────────────────────────────────
const SiraMap: React.FC = () => {
  const mapRef = useRef<LeafletMap | null>(null)
  const { vessels, history } = useVesselMovement()
  const [activeRegion, setActiveRegion] = useState<string | null>(null)

  const [layers, setLayers] = useState<LayerState>({
    vessels: true, ports: true, corridors: true, railways: true,
    gasStations: true, mining: true, oilGas: true, energy: true, trucks: true,
  })

  const toggleLayer = useCallback((key: keyof LayerState) => {
    setLayers(prev => ({ ...prev, [key]: !prev[key] }))
  }, [])

  // Tile layer: Mapbox dark if token present, else CartoDB
  const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN as string | undefined
  const tileUrl = MAPBOX_TOKEN
    ? `https://api.mapbox.com/styles/v1/mapbox/dark-v11/tiles/{z}/{x}/{y}?access_token=${MAPBOX_TOKEN}`
    : 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
  const tileAttrib = MAPBOX_TOKEN
    ? '© Mapbox © OpenStreetMap'
    : '© CartoDB © OpenStreetMap'
  const tileOpts = MAPBOX_TOKEN ? { tileSize: 512 as const, zoomOffset: -1 } : {}

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      {/* Sidebar */}
      <MapSidebar mapRef={mapRef} layers={layers} onToggleLayer={toggleLayer} />

      {/* Top bar */}
      <TopBar mapRef={mapRef} activeRegion={activeRegion} setActiveRegion={setActiveRegion} />

      {/* Map */}
      <MapContainer
        center={[5, 20]}
        zoom={4}
        minZoom={3}
        maxZoom={12}
        style={{ position: 'absolute', top: 0, left: 272, right: 0, bottom: 0 }}
        zoomControl={false}
      >
        <MapRefCapture mapRef={mapRef} />
        <TileLayer url={tileUrl} attribution={tileAttrib} {...tileOpts} />

        {/* ── Corridors ────────────────────────────────────────────────────── */}
        {layers.corridors && corridors.map(c => (
          <Polyline key={c.id} positions={c.path as [number,number][]} color={c.color} weight={c.weight} opacity={0.75}>
            <Popup {...popupOpts}>
              <div style={{ minWidth: 160 }}>
                <p style={{ color: '#00ffcc', fontWeight: 700, margin: '0 0 6px', fontSize: 13 }}>{c.name}</p>
                <LoginGate />
              </div>
            </Popup>
          </Polyline>
        ))}

        {/* ── Railways ─────────────────────────────────────────────────────── */}
        {layers.railways && railways.map(r => (
          <Polyline key={r.id} positions={r.path as [number,number][]} color={r.color} weight={r.weight} dashArray={r.dashArray} opacity={0.7}>
            <Popup {...popupOpts}>
              <div style={{ minWidth: 160 }}>
                <p style={{ color: '#a855f7', fontWeight: 700, margin: '0 0 6px', fontSize: 13 }}>{r.name}</p>
                <LoginGate />
              </div>
            </Popup>
          </Polyline>
        ))}

        {/* ── Vessel trails ─────────────────────────────────────────────────── */}
        {layers.vessels && vessels.map(v => {
          const trail = history[v.id]
          if (!trail || trail.length < 2) return null
          const color = VESSEL_COLORS[v.type] || '#00ffcc'
          return (
            <Polyline
              key={`trail-${v.id}`}
              positions={trail}
              color={color}
              weight={1}
              opacity={0.35}
            />
          )
        })}

        {/* ── Vessels ───────────────────────────────────────────────────────── */}
        {layers.vessels && vessels.map(v => {
          const color = VESSEL_COLORS[v.type] || '#00ffcc'
          return (
            <CircleMarker
              key={v.id}
              center={[v.lat, v.lng]}
              radius={v.type === 'offshore' || v.type === 'fpso' ? 5 : 4}
              pathOptions={{ color, fillColor: color, fillOpacity: 0.9, weight: 1 }}
            >
              <Popup {...popupOpts}>
                <div style={{ minWidth: 180 }}>
                  <p style={{ color, fontWeight: 700, margin: '0 0 8px', fontSize: 13 }}>
                    {v.flag} {v.name}
                  </p>
                  <Row label="Type" value={v.type} />
                  <Row label="IMO" value={v.imo} />
                  <Row label="Heading" value={`${Math.round(v.heading)}°`} />
                  <LoginGate />
                </div>
              </Popup>
            </CircleMarker>
          )
        })}

        {/* ── Ports ─────────────────────────────────────────────────────────── */}
        {layers.ports && coastalPorts.map(p => (
          <CircleMarker
            key={p.id}
            center={p.coords}
            radius={7}
            pathOptions={{ color: '#00b4ff', fillColor: '#00b4ff', fillOpacity: 0.85, weight: 1.5 }}
          >
            <Popup {...popupOpts}>
              <div style={{ minWidth: 200 }}>
                <p style={{ color: '#00b4ff', fontWeight: 700, margin: '0 0 8px', fontSize: 13 }}>
                  🏗️ {p.name}
                </p>
                <Row label="Country" value={p.country} />
                <Row label="Active Vessels" value={p.vessels} />
                <Row label="Annual Volume" value={p.volume} />
                <LoginGate />
              </div>
            </Popup>
          </CircleMarker>
        ))}

        {/* ── Mining ────────────────────────────────────────────────────────── */}
        {layers.mining && miningSites.map(m => (
          <CircleMarker
            key={m.id}
            center={m.coords}
            radius={6}
            pathOptions={{ color: '#fbbf24', fillColor: '#fbbf24', fillOpacity: 0.8, weight: 1 }}
          >
            <Popup {...popupOpts}>
              <div style={{ minWidth: 190 }}>
                <p style={{ color: '#fbbf24', fontWeight: 700, margin: '0 0 8px', fontSize: 13 }}>
                  ⛏️ {m.name}
                </p>
                <Row label="Country" value={m.country} />
                <Row label="Type" value={m.type} />
                <Row label="Operator" value={m.operator} />
                <LoginGate />
              </div>
            </Popup>
          </CircleMarker>
        ))}

        {/* ── Oil & Gas ─────────────────────────────────────────────────────── */}
        {layers.oilGas && oilGasSites.map(o => (
          <CircleMarker
            key={o.id}
            center={o.coords}
            radius={5}
            pathOptions={{ color: '#f43f5e', fillColor: '#f43f5e', fillOpacity: 0.8, weight: 1 }}
          >
            <Popup {...popupOpts}>
              <div style={{ minWidth: 190 }}>
                <p style={{ color: '#f43f5e', fontWeight: 700, margin: '0 0 8px', fontSize: 13 }}>
                  🛢️ {o.name}
                </p>
                <Row label="Country" value={o.country} />
                <Row label="Type" value={o.type} />
                <Row label="Production" value={o.production} />
                <LoginGate />
              </div>
            </Popup>
          </CircleMarker>
        ))}

        {/* ── Energy ────────────────────────────────────────────────────────── */}
        {layers.energy && energySites.map(e => (
          <CircleMarker
            key={e.id}
            center={e.coords}
            radius={5}
            pathOptions={{ color: '#fb923c', fillColor: '#fb923c', fillOpacity: 0.8, weight: 1 }}
          >
            <Popup {...popupOpts}>
              <div style={{ minWidth: 190 }}>
                <p style={{ color: '#fb923c', fontWeight: 700, margin: '0 0 8px', fontSize: 13 }}>
                  ⚡ {e.name}
                </p>
                <Row label="Country" value={e.country} />
                <Row label="Type" value={e.type} />
                <Row label="Capacity" value={e.capacity} />
                <LoginGate />
              </div>
            </Popup>
          </CircleMarker>
        ))}

        {/* ── Gas Stations ──────────────────────────────────────────────────── */}
        {layers.gasStations && gasStations.map(g => (
          <CircleMarker
            key={g.id}
            center={g.coords}
            radius={4}
            pathOptions={{ color: '#fef08a', fillColor: '#fef08a', fillOpacity: 0.8, weight: 1 }}
          >
            <Popup {...popupOpts}>
              <div style={{ minWidth: 170 }}>
                <p style={{ color: '#fef08a', fontWeight: 700, margin: '0 0 8px', fontSize: 13 }}>
                  ⛽ {g.name}
                </p>
                <Row label="Brand" value={g.brand} />
                <LoginGate />
              </div>
            </Popup>
          </CircleMarker>
        ))}

        {/* ── Trucks ────────────────────────────────────────────────────────── */}
        {layers.trucks && trucks.map(t => (
          <CircleMarker
            key={t.id}
            center={t.coords}
            radius={4}
            pathOptions={{ color: '#f97316', fillColor: '#f97316', fillOpacity: 0.85, weight: 1 }}
          >
            <Popup {...popupOpts}>
              <div style={{ minWidth: 200 }}>
                <p style={{ color: '#f97316', fontWeight: 700, margin: '0 0 8px', fontSize: 13 }}>
                  🚛 {t.name}
                </p>
                <Row label="Route" value={t.route} />
                <Row label="Cargo" value={t.cargo} />
                <LoginGate />
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>

      {/* Legend */}
      <div style={{ position: 'absolute', bottom: 0, left: 272, right: 0 }}>
        <MapLegend />
      </div>
    </div>
  )
}

export default SiraMap
