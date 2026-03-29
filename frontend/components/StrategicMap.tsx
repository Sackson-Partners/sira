/**
 * SIRA Strategic Intelligence Map (SIM)
 * Phase 2 — Mapbox GL JS v3 | Real-time Fleet + Maritime + AI Risk Overlays
 *
 * Layers:
 *  - Truck Fleet (Flespi real-time via WebSocket)
 *  - Vessel Tracking (MarineTraffic AIS)
 *  - AI Risk Heatmap
 *  - Port Status
 *  - Storage Levels
 *  - Alert Markers
 */

'use client'

import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { useEffect, useRef, useState, useCallback } from 'react'

mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN!

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const WS_BASE = API_BASE.replace(/^http/, 'ws')

interface Vehicle {
    id: string
    lat: number
    lon: number
    speed: number
    status: 'idle' | 'active' | 'maintenance' | 'offline' | 'alert'
    plate: string
    driver?: string
    fuel_level?: number
}

interface Vessel {
    mmsi: string
    vessel_name: string
    lat: number
    lon: number
    speed: number
    destination?: string
    eta?: string
}

interface AlertMarker {
    id: string
    lat: number
    lon: number
    type: string
    severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
    message: string
}

const STATUS_COLORS: Record<Vehicle['status'], string> = {
    idle: '#94a3b8',
    active: '#22c55e',
    maintenance: '#f59e0b',
    offline: '#6b7280',
    alert: '#ef4444',
}

const SEVERITY_COLORS: Record<AlertMarker['severity'], string> = {
    LOW: '#22c55e',
    MEDIUM: '#f59e0b',
    HIGH: '#f97316',
    CRITICAL: '#ef4444',
}

export default function StrategicMap() {
    const mapContainer = useRef<HTMLDivElement>(null)
    const mapRef = useRef<mapboxgl.Map | null>(null)
    const markersRef = useRef<Map<string, mapboxgl.Marker>>(new Map())
    const wsRef = useRef<WebSocket | null>(null)
    const [mapLoaded, setMapLoaded] = useState(false)
    const [vehicleCount, setVehicleCount] = useState(0)
    const [vesselCount, setVesselCount] = useState(0)
    const [activeAlerts, setActiveAlerts] = useState(0)

  // ---------------------------------------------------------------------------
  // Initialise Mapbox
  // ---------------------------------------------------------------------------
  useEffect(() => {
        if (!mapContainer.current || mapRef.current) return

                mapRef.current = new mapboxgl.Map({
                        container: mapContainer.current,
                        style: 'mapbox://styles/mapbox/dark-v11',
                        center: [0, 5],
                        zoom: 3,
                        projection: 'mercator',
                })

                mapRef.current.addControl(new mapboxgl.NavigationControl(), 'top-right')
        mapRef.current.addControl(new mapboxgl.ScaleControl(), 'bottom-left')
        mapRef.current.addControl(new mapboxgl.FullscreenControl(), 'top-right')

                mapRef.current.on('load', () => {
                        setMapLoaded(true)
                        initLayers()
                        fetchStaticData()
                })

                return () => {
                        wsRef.current?.close()
                        mapRef.current?.remove()
                        mapRef.current = null
                }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // ---------------------------------------------------------------------------
  // Initialise data sources and layers
  // ---------------------------------------------------------------------------
  const initLayers = useCallback(() => {
        const map = mapRef.current
        if (!map) return

                                     // Truck fleet source (GeoJSON — updated by WebSocket)
                                     map.addSource('trucks', {
                                             type: 'geojson',
                                             data: { type: 'FeatureCollection', features: [] },
                                     })

                                     // Vessel positions source
                                     map.addSource('vessels', {
                                             type: 'geojson',
                                             data: { type: 'FeatureCollection', features: [] },
                                     })

                                     // AI Risk heatmap source
                                     map.addSource('risk-heatmap', {
                                             type: 'geojson',
                                             data: { type: 'FeatureCollection', features: [] },
                                     })

                                     // Alert markers source
                                     map.addSource('alerts', {
                                             type: 'geojson',
                                             data: { type: 'FeatureCollection', features: [] },
                                     })

                                     // Truck layer
                                     map.addLayer({
                                             id: 'truck-layer',
                                             type: 'circle',
                                             source: 'trucks',
                                             paint: {
                                                       'circle-radius': 8,
                                                       'circle-color': [
                                                                   'match',
                                                                   ['get', 'status'],
                                                                   'active', '#22c55e',
                                                                   'idle', '#94a3b8',
                                                                   'maintenance', '#f59e0b',
                                                                   'alert', '#ef4444',
                                                                   '#6b7280',
                                                                 ],
                                                       'circle-stroke-width': 2,
                                                       'circle-stroke-color': '#ffffff',
                                                       'circle-opacity': 0.9,
                                             },
                                     })

                                     // Truck labels
                                     map.addLayer({
                                             id: 'truck-labels',
                                             type: 'symbol',
                                             source: 'trucks',
                                             layout: {
                                                       'text-field': ['get', 'plate'],
                                                       'text-size': 10,
                                                       'text-offset': [0, 1.5],
                                                       'text-anchor': 'top',
                                             },
                                             paint: {
                                                       'text-color': '#ffffff',
                                                       'text-halo-color': '#000000',
                                                       'text-halo-width': 1,
                                             },
                                     })

                                     // Vessel layer
                                     map.addLayer({
                                             id: 'vessel-layer',
                                             type: 'circle',
                                             source: 'vessels',
                                             paint: {
                                                       'circle-radius': 7,
                                                       'circle-color': '#3b82f6',
                                                       'circle-stroke-width': 2,
                                                       'circle-stroke-color': '#93c5fd',
                                                       'circle-opacity': 0.85,
                                             },
                                     })

                                     // Vessel labels
                                     map.addLayer({
                                             id: 'vessel-labels',
                                             type: 'symbol',
                                             source: 'vessels',
                                             layout: {
                                                       'text-field': ['get', 'vessel_name'],
                                                       'text-size': 10,
                                                       'text-offset': [0, 1.5],
                                                       'text-anchor': 'top',
                                             },
                                             paint: {
                                                       'text-color': '#93c5fd',
                                                       'text-halo-color': '#000000',
                                                       'text-halo-width': 1,
                                             },
                                     })

                                     // AI Risk heatmap
                                     map.addLayer({
                                             id: 'risk-heatmap-layer',
                                             type: 'heatmap',
                                             source: 'risk-heatmap',
                                             paint: {
                                                       'heatmap-weight': ['interpolate', ['linear'], ['get', 'risk_score'], 0, 0, 1, 1],
                                                       'heatmap-intensity': 1.5,
                                                       'heatmap-color': [
                                                                   'interpolate',
                                                                   ['linear'],
                                                                   ['heatmap-density'],
                                                                   0, 'rgba(0,0,0,0)',
                                                                   0.3, 'rgba(34,197,94,0.5)',
                                                                   0.6, 'rgba(234,179,8,0.7)',
                                                                   0.8, 'rgba(249,115,22,0.8)',
                                                                   1, 'rgba(239,68,68,0.9)',
                                                                 ],
                                                       'heatmap-radius': 30,
                                                       'heatmap-opacity': 0.6,
                                             },
                                     })

                                     // Alert markers
                                     map.addLayer({
                                             id: 'alert-layer',
                                             type: 'circle',
                                             source: 'alerts',
                                             paint: {
                                                       'circle-radius': ['interpolate', ['linear'], ['zoom'], 3, 6, 10, 12],
                                                       'circle-color': [
                                                                   'match',
                                                                   ['get', 'severity'],
                                                                   'CRITICAL', '#ef4444',
                                                                   'HIGH', '#f97316',
                                                                   'MEDIUM', '#f59e0b',
                                                                   '#22c55e',
                                                                 ],
                                                       'circle-stroke-width': 2,
                                                       'circle-stroke-color': '#ffffff',
                                                       'circle-opacity': 0.95,
                                                       'circle-pitch-alignment': 'map',
                                             },
                                     })

                                     // Popups for trucks
                                     map.on('click', 'truck-layer', (e) => {
                                             const feature = e.features?.[0]
                                             if (!feature) return
                                             const props = feature.properties as any
                                             new mapboxgl.Popup({ maxWidth: '280px' })
                                               .setLngLat(e.lngLat)
                                               .setHTML(`
                                                         <div class="p-3 text-sm">
                                                                     <h3 class="font-bold text-base mb-2">${props.plate}</h3>
                                                                                 <div class="space-y-1">
                                                                                               <p>Status: <span class="font-medium capitalize">${props.status}</span></p>
                                                                                                             <p>Speed: ${props.speed} km/h</p>
                                                                                                                           ${props.fuel_level !== null ? `<p>Fuel: ${props.fuel_level}%</p>` : ''}
                                                                                                                                         ${props.driver ? `<p>Driver: ${props.driver}</p>` : ''}
                                                                                                                                                     </div>
                                                                                                                                                               </div>
                                                                                                                                                                       `)
                                               .addTo(map)
                                     })

                                     // Popups for vessels
                                     map.on('click', 'vessel-layer', (e) => {
                                             const feature = e.features?.[0]
                                             if (!feature) return
                                             const props = feature.properties as any
                                             new mapboxgl.Popup({ maxWidth: '280px' })
                                               .setLngLat(e.lngLat)
                                               .setHTML(`
                                                         <div class="p-3 text-sm">
                                                                     <h3 class="font-bold text-base mb-2">${props.vessel_name}</h3>
                                                                                 <div class="space-y-1">
                                                                                               <p>MMSI: ${props.mmsi}</p>
                                                                                                             <p>Speed: ${props.speed} knots</p>
                                                                                                                           ${props.destination ? `<p>Destination: ${props.destination}</p>` : ''}
                                                                                                                                         ${props.eta ? `<p>ETA: ${new Date(props.eta).toLocaleDateString()}</p>` : ''}
                                                                                                                                                     </div>
                                                                                                                                                               </div>
                                                                                                                                                                       `)
                                               .addTo(map)
                                     })

                                     map.on('mouseenter', 'truck-layer', () => { map.getCanvas().style.cursor = 'pointer' })
        map.on('mouseleave', 'truck-layer', () => { map.getCanvas().style.cursor = '' })
        map.on('mouseenter', 'vessel-layer', () => { map.getCanvas().style.cursor = 'pointer' })
        map.on('mouseleave', 'vessel-layer', () => { map.getCanvas().style.cursor = '' })
  }, [])

  // ---------------------------------------------------------------------------
  // Fetch static/polled data
  // ---------------------------------------------------------------------------
  const fetchStaticData = useCallback(async () => {
        const token = localStorage.getItem('sira_token')
        const headers = token ? { Authorization: `Bearer ${token}` } : {}

              try {
                      // Fetch vessel positions (every 5 min)
          const vesselRes = await fetch(`${API_BASE}/api/v2/maritime/vessels/geojson`, { headers })
                      if (vesselRes.ok) {
                                const vesselGeo = await vesselRes.json()
                                const source = mapRef.current?.getSource('vessels') as mapboxgl.GeoJSONSource
                                source?.setData(vesselGeo)
                                setVesselCount(vesselGeo.features?.length || 0)
                      }

          // Fetch AI risk heatmap
          const riskRes = await fetch(`${API_BASE}/api/v2/ai/risk-heatmap`, { headers })
                      if (riskRes.ok) {
                                const riskGeo = await riskRes.json()
                                const source = mapRef.current?.getSource('risk-heatmap') as mapboxgl.GeoJSONSource
                                source?.setData(riskGeo)
                      }

          // Fetch active alerts
          const alertsRes = await fetch(`${API_BASE}/api/v2/fleet/alerts?resolved=false&limit=100`, { headers })
                      if (alertsRes.ok) {
                                const alertsData = await alertsRes.json()
                                const alertFeatures = alertsData.items
                                  ?.filter((a: any) => a.lat && a.lon)
                                  .map((a: any) => ({
                                                type: 'Feature',
                                                geometry: { type: 'Point', coordinates: [a.lon, a.lat] },
                                                properties: { id: a.id, type: a.type, severity: a.severity, message: a.message },
                                  })) || []
                                          const source = mapRef.current?.getSource('alerts') as mapboxgl.GeoJSONSource
                                source?.setData({ type: 'FeatureCollection', features: alertFeatures })
                                setActiveAlerts(alertsData.total || 0)
                      }
              } catch (err) {
                      console.warn('[StrategicMap] Data fetch error:', err)
              }
  }, [])

  // ---------------------------------------------------------------------------
  // WebSocket for real-time truck positions
  // ---------------------------------------------------------------------------
  useEffect(() => {
        if (!mapLoaded) return

                const token = localStorage.getItem('sira_token')
        const wsUrl = `${WS_BASE}/ws/fleet?token=${token || ''}`

                const connectWS = () => {
                        const ws = new WebSocket(wsUrl)
                        wsRef.current = ws

                        ws.onmessage = (event) => {
                                  try {
                                              const data = JSON.parse(event.data)
                                              if (data.type === 'fleet_update') {
                                                            const source = mapRef.current?.getSource('trucks') as mapboxgl.GeoJSONSource
                                                            source?.setData(data.geojson)
                                                            setVehicleCount(data.geojson.features?.length || 0)
                                              }
                                  } catch {}
                        }

                        ws.onclose = () => {
                                  // Reconnect after 5s
                                  setTimeout(connectWS, 5000)
                        }

                        ws.onerror = (err) => {
                                  console.warn('[StrategicMap] WebSocket error:', err)
                                  ws.close()
                        }
                }

                connectWS()

                // Poll vessel/risk data every 5 minutes
                const pollInterval = setInterval(fetchStaticData, 5 * 60 * 1000)

                return () => {
                        clearInterval(pollInterval)
                        wsRef.current?.close()
                }
  }, [mapLoaded, fetchStaticData])

  return (
        <div className="relative w-full h-full">
          {/* Map container */}
              <div ref={mapContainer} className="w-full h-full" />
        
          {/* HUD Overlay */}
              <div className="absolute top-4 left-4 flex flex-col gap-2 pointer-events-none">
                      <div className="bg-gray-900/90 backdrop-blur border border-gray-700 rounded-lg px-4 py-3 text-white text-sm">
                                <p className="text-xs text-gray-400 mb-1">SIRA Strategic Intelligence Map</p>
                                <div className="flex gap-4">
                                            <span className="flex items-center gap-1.5">
                                                          <span className="w-2.5 h-2.5 rounded-full bg-green-500 inline-block" />
                                              {vehicleCount} Vehicles
                                            </span>
                                            <span className="flex items-center gap-1.5">
                                                          <span className="w-2.5 h-2.5 rounded-full bg-blue-400 inline-block" />
                                              {vesselCount} Vessels
                                            </span>
                                            <span className="flex items-center gap-1.5">
                                                          <span className="w-2.5 h-2.5 rounded-full bg-red-500 inline-block" />
                                              {activeAlerts} Alerts
                                            </span>
                                </div>
                      </div>
              </div>
        
          {/* Legend */}
              <div className="absolute bottom-8 right-4 bg-gray-900/90 backdrop-blur border border-gray-700 rounded-lg px-4 py-3 text-white text-xs pointer-events-none">
                      <p className="font-semibold mb-2 text-gray-300">AI Risk Level</p>
                {[
          { color: 'bg-red-500', label: 'Critical Risk' },
          { color: 'bg-orange-500', label: 'High Risk' },
          { color: 'bg-yellow-500', label: 'Medium Risk' },
          { color: 'bg-green-500', label: 'Low Risk' },
                  ].map(({ color, label }) => (
                              <div key={label} className="flex items-center gap-2 mb-1">
                                          <span className={`w-3 h-3 rounded-sm ${color}`} />
                                          <span>{label}</span>
                              </div>
                            ))}
              </div>
        </div>
      )
}
