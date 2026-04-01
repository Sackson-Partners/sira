import { useState, useEffect, useRef } from 'react'
import { initialVessels, Vessel } from '../data/infrastructure'

type TrailHistory = Record<string, [number, number][]>

export function useVesselMovement() {
  const [vessels, setVessels] = useState<Vessel[]>(initialVessels)
  const [history, setHistory] = useState<TrailHistory>({})
  const vesselsRef = useRef(vessels)
  vesselsRef.current = vessels

  // Smooth position update
  useEffect(() => {
    const id = setInterval(() => {
      setVessels(prev =>
        prev.map(v => {
          const rad = (v.heading * Math.PI) / 180
          return {
            ...v,
            lat: v.lat + Math.cos(rad) * v.speed,
            lng: v.lng + Math.sin(rad) * v.speed,
          }
        })
      )
    }, 1500)
    return () => clearInterval(id)
  }, [])

  // Gradual heading drift
  useEffect(() => {
    const id = setInterval(() => {
      setVessels(prev =>
        prev.map(v => ({
          ...v,
          heading:
            v.type === 'offshore' || v.type === 'fpso'
              ? v.heading
              : v.heading + (Math.random() * 10 - 5),
        }))
      )
    }, 4000)
    return () => clearInterval(id)
  }, [])

  // Trail history
  useEffect(() => {
    const id = setInterval(() => {
      setHistory(prev => {
        const next: TrailHistory = {}
        vesselsRef.current.forEach(v => {
          const existing = prev[v.id] || []
          next[v.id] = [...existing, [v.lat, v.lng]].slice(-25) as [number, number][]
        })
        return next
      })
    }, 1500)
    return () => clearInterval(id)
  }, [])

  return { vessels, history }
}
