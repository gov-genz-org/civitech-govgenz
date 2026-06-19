import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import ReactGA from 'react-ga4'

/**
 * Hook à placer dans App.jsx pour tracker automatiquement
 * chaque changement de page dans Google Analytics 4.
 */
export function usePageTracking() {
  const location = useLocation()

  useEffect(() => {
    if (!import.meta.env.VITE_GA_MEASUREMENT_ID) return
    ReactGA.send({ hitType: 'pageview', page: location.pathname + location.search })
  }, [location])
}
