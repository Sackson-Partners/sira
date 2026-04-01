import React from 'react'

const LEGEND = [
  { color: '#00b4ff', label: 'Port',      shape: 'circle' },
  { color: '#00ffcc', label: 'Vessel',    shape: 'circle' },
  { color: '#f59e0b', label: 'Corridor',  shape: 'line' },
  { color: '#a855f7', label: 'Railway',   shape: 'dashed' },
  { color: '#fbbf24', label: 'Mining',    shape: 'circle' },
  { color: '#f43f5e', label: 'Oil & Gas', shape: 'circle' },
  { color: '#fb923c', label: 'Energy',    shape: 'circle' },
  { color: '#fef08a', label: 'Fuel',      shape: 'circle' },
  { color: '#f97316', label: 'Truck',     shape: 'circle' },
]

const MapLegend: React.FC = () => (
  <div
    style={{
      position: 'absolute',
      bottom: 28,
      right: 12,
      zIndex: 1000,
      background: 'rgba(11,15,23,0.88)',
      backdropFilter: 'blur(8px)',
      border: '1px solid rgba(0,255,204,0.18)',
      borderRadius: 8,
      padding: '10px 14px',
      display: 'flex',
      flexWrap: 'wrap',
      gap: '6px 14px',
      maxWidth: 340,
    }}
  >
    {LEGEND.map(item => (
      <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        {item.shape === 'line' ? (
          <div style={{ width: 16, height: 2, background: item.color, borderRadius: 1 }} />
        ) : item.shape === 'dashed' ? (
          <div
            style={{
              width: 16,
              height: 2,
              background: `repeating-linear-gradient(90deg,${item.color} 0 4px,transparent 4px 8px)`,
            }}
          />
        ) : (
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: item.color,
              boxShadow: `0 0 6px ${item.color}`,
            }}
          />
        )}
        <span style={{ color: '#94a3b8', fontSize: 11 }}>{item.label}</span>
      </div>
    ))}
  </div>
)

export default MapLegend
