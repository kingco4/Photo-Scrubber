import { useEffect, useRef, useState } from 'react'

import { API_BASE, DEFAULT_LIVE_INTERVAL_MS, DEFAULT_LIVE_JPEG_QUALITY, DEFAULT_LIVE_MAX_DIMENSION } from '../constants'
import { canvasToBlob } from '../utils/media'
import { validateBlurStrength, validateLiveSettings } from '../utils/fileValidation'

export function useLiveScrubber({ blurPeople, blurStrength, detectBodies, isAuthenticated, onUnauthorized, removeText }) {
  const videoRef = useRef(null)
  const captureCanvasRef = useRef(null)
  const streamRef = useRef(null)
  const liveLoopTimeoutRef = useRef(null)
  const liveRequestInFlightRef = useRef(false)
  const liveActiveRef = useRef(false)
  const latestLiveUrlRef = useRef('')
  const optionsRef = useRef({})
  const [liveSupported, setLiveSupported] = useState(false)
  const [liveActive, setLiveActive] = useState(false)
  const [liveBusy, setLiveBusy] = useState(false)
  const [liveError, setLiveError] = useState('')
  const [liveFrameUrl, setLiveFrameUrl] = useState('')
  const [liveStatus, setLiveStatus] = useState('Idle')
  const [liveMaxDimension, setLiveMaxDimension] = useState(DEFAULT_LIVE_MAX_DIMENSION)
  const [liveJpegQuality, setLiveJpegQuality] = useState(DEFAULT_LIVE_JPEG_QUALITY)
  const [liveIntervalMs, setLiveIntervalMs] = useState(DEFAULT_LIVE_INTERVAL_MS)
  const [liveStats, setLiveStats] = useState(null)

  useEffect(() => {
    optionsRef.current = { blurPeople, blurStrength, detectBodies, liveIntervalMs, liveJpegQuality, liveMaxDimension, removeText }
  }, [blurPeople, blurStrength, detectBodies, liveIntervalMs, liveJpegQuality, liveMaxDimension, removeText])

  useEffect(() => {
    setLiveSupported(typeof navigator !== 'undefined' && !!navigator.mediaDevices?.getUserMedia)
    return () => stopLiveSession()
  }, [])

  function replaceLiveFrameUrl(blob) {
    if (latestLiveUrlRef.current) URL.revokeObjectURL(latestLiveUrlRef.current)
    const nextUrl = URL.createObjectURL(blob)
    latestLiveUrlRef.current = nextUrl
    setLiveFrameUrl(nextUrl)
  }

  function stopLiveSession() {
    if (latestLiveUrlRef.current) URL.revokeObjectURL(latestLiveUrlRef.current)
    if (liveLoopTimeoutRef.current) window.clearTimeout(liveLoopTimeoutRef.current)
    if (streamRef.current) streamRef.current.getTracks().forEach((track) => track.stop())
    if (videoRef.current) videoRef.current.srcObject = null
    liveLoopTimeoutRef.current = null
    streamRef.current = null
    liveActiveRef.current = false
    liveRequestInFlightRef.current = false
    latestLiveUrlRef.current = ''
    setLiveActive(false)
    setLiveBusy(false)
    setLiveStatus('Idle')
  }

  function handleLiveFailure(message) {
    setLiveError(message)
    setLiveStatus('Live scrub stopped')
    stopLiveSession()
  }

  async function captureLiveFrame() {
    if (!liveActiveRef.current || liveRequestInFlightRef.current) return
    const settingsError = validateLiveSettings(liveMaxDimension, liveJpegQuality, liveIntervalMs)
    if (settingsError) return handleLiveFailure(settingsError)
    const video = videoRef.current
    const canvas = captureCanvasRef.current
    if (!video || !canvas || video.videoWidth === 0 || video.videoHeight === 0 || video.readyState < 2) {
      liveLoopTimeoutRef.current = window.setTimeout(captureLiveFrame, liveIntervalMs)
      return
    }
    if (streamRef.current && !streamRef.current.getVideoTracks().some((track) => track.readyState === 'live')) return handleLiveFailure('Webcam stream ended.')
    const scale = Math.min(1, liveMaxDimension / Math.max(video.videoWidth, video.videoHeight))
    const width = Math.max(1, Math.round(video.videoWidth * scale))
    const height = Math.max(1, Math.round(video.videoHeight * scale))
    canvas.width = width
    canvas.height = height
    const context = canvas.getContext('2d', { alpha: false })
    if (!context) return handleLiveFailure('Unable to create a 2D canvas context for live capture.')
    context.drawImage(video, 0, 0, width, height)
    liveRequestInFlightRef.current = true
    setLiveBusy(true)
    setLiveStatus('Processing live frame')
    const started = performance.now()
    try {
      const blob = await canvasToBlob(canvas, 'image/jpeg', Math.min(0.95, Math.max(0.4, liveJpegQuality / 100)))
      const form = new FormData()
      form.append('file', blob, 'live-frame.jpg')
      form.append('blur_people', String(optionsRef.current.blurPeople))
      form.append('remove_text', String(optionsRef.current.removeText))
      form.append('detect_bodies', String(optionsRef.current.detectBodies))
      form.append('blur_strength', String(optionsRef.current.blurStrength))
      form.append('max_dimension', String(optionsRef.current.liveMaxDimension))
      form.append('jpeg_quality', String(optionsRef.current.liveJpegQuality))
      const res = await fetch(`${API_BASE}/process/live`, { method: 'POST', body: form, credentials: 'include' })
      if (!res.ok) {
        const text = await res.text()
        if (res.status === 401) onUnauthorized?.()
        throw new Error(`Live server error (${res.status}): ${text.slice(0, 200)}`)
      }
      replaceLiveFrameUrl(await res.blob())
      setLiveStats({ latencyMs: Math.round(performance.now() - started), sentWidth: width, sentHeight: height })
      setLiveError('')
      setLiveStatus('Live scrub running')
    } catch (error) {
      handleLiveFailure(error?.message || 'Live scrub failed')
      return
    } finally {
      liveRequestInFlightRef.current = false
      setLiveBusy(false)
    }
    if (liveActiveRef.current) liveLoopTimeoutRef.current = window.setTimeout(captureLiveFrame, liveIntervalMs)
  }

  async function startLiveSession() {
    if (!isAuthenticated) return setLiveError('Sign in before starting live scrub.')
    if (!liveSupported) return setLiveError('This browser does not support webcam capture.')
    const validationError = validateBlurStrength(blurStrength) || validateLiveSettings(liveMaxDimension, liveJpegQuality, liveIntervalMs)
    if (validationError) return setLiveError(validationError)
    if (!blurPeople && !removeText) return setLiveError('Enable text removal or people blurring before starting live scrub.')
    stopLiveSession()
    setLiveError('')
    setLiveStatus('Starting camera')
    try {
      streamRef.current = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false })
      if (videoRef.current) {
        videoRef.current.srcObject = streamRef.current
        await videoRef.current.play()
      }
      liveActiveRef.current = true
      setLiveActive(true)
      setLiveStatus('Camera ready')
      liveLoopTimeoutRef.current = window.setTimeout(captureLiveFrame, 120)
    } catch (error) {
      setLiveError(error?.message || 'Unable to start webcam.')
      stopLiveSession()
    }
  }

  return {
    captureCanvasRef, liveActive, liveBusy, liveError, liveFrameUrl, liveIntervalMs, liveJpegQuality, liveMaxDimension, liveStats, liveStatus, liveSupported, setLiveIntervalMs, setLiveJpegQuality, setLiveMaxDimension, startLiveSession, stopLiveSession, videoRef,
  }
}
