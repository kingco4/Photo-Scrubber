import { useEffect, useRef, useState } from 'react'

import { DEFAULT_SCRUB_ESTIMATE_MS } from '../constants'

export function useCountdown(active) {
  const startedAtRef = useRef(0)
  const [etaMs, setEtaMs] = useState(DEFAULT_SCRUB_ESTIMATE_MS)
  const [countdownMs, setCountdownMs] = useState(0)
  const [lastDurationMs, setLastDurationMs] = useState(0)

  useEffect(() => {
    if (!active) {
      setCountdownMs(0)
      return
    }
    const tick = () => setCountdownMs(Math.max(0, etaMs - (performance.now() - startedAtRef.current)))
    tick()
    const intervalId = window.setInterval(tick, 200)
    return () => window.clearInterval(intervalId)
  }, [active, etaMs])

  function start() {
    startedAtRef.current = performance.now()
  }

  function complete() {
    const elapsedMs = performance.now() - startedAtRef.current
    setLastDurationMs(Math.round(elapsedMs))
    setEtaMs((current) => (!current || current <= 0 ? Math.round(elapsedMs) : Math.round(current * 0.6 + elapsedMs * 0.4)))
  }

  return { countdownMs, etaMs, lastDurationMs, start, complete }
}
