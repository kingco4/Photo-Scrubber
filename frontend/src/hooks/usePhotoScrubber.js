import { useRef, useState } from 'react'

import { API_BASE, VALIDATION_SKIP_THRESHOLD } from '../constants'
import { ACCEPTED_IMAGE_LABEL, isHeifFamilyFile } from '../fileTypes'
import { useCountdown } from './useCountdown'
import { readImageDimensions, validateBlurStrength, validateImageDimensions, validateSelectedFile } from '../utils/fileValidation'

export function usePhotoScrubber({ isAuthenticated, onUnauthorized, setIpUploadCount, setSkipUploadValidations, skipUploadValidations }) {
  const inputRef = useRef(null)
  const [file, setFile] = useState(null)
  const [fileMeta, setFileMeta] = useState(null)
  const [fileNote, setFileNote] = useState('')
  const [blurPeople, setBlurPeople] = useState(true)
  const [removeText, setRemoveText] = useState(true)
  const [detectBodies, setDetectBodies] = useState(false)
  const [blurStrength, setBlurStrength] = useState(31)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [outBlob, setOutBlob] = useState(null)
  const countdown = useCountdown(busy)

  async function onFileChange(event) {
    const nextFile = event.target.files?.[0] || null
    setOutBlob(null)
    if (!nextFile) return resetSelection()
    if (!skipUploadValidations) {
      const validationError = validateSelectedFile(nextFile)
      if (validationError) return rejectSelection(event, validationError)
    }
    try {
      if (skipUploadValidations) {
        setFile(nextFile)
        setFileMeta(null)
        setFileNote(`Pre-upload checks are skipped after ${VALIDATION_SKIP_THRESHOLD} uploads from this IP address.`)
        setError('')
        return
      }
      if (isHeifFamilyFile(nextFile)) {
        setFile(nextFile)
        setFileMeta(null)
        setFileNote('HEIC/HEIF validation is completed on the server. Input preview may be unavailable in this browser.')
        setError('')
        return
      }
      const dimensions = await readImageDimensions(nextFile)
      const dimensionsError = validateImageDimensions(dimensions)
      if (dimensionsError) throw new Error(dimensionsError)
      setFile(nextFile)
      setFileMeta(dimensions)
      setFileNote('')
      setError('')
    } catch (error) {
      rejectSelection(event, error?.message || 'Invalid image.')
    }
  }

  async function onProcess() {
    if (!file || !isAuthenticated) return
    const validationError = validateSelectedFile(file) || validateBlurStrength(blurStrength)
    if (validationError) return setError(validationError)
    if (!blurPeople && !removeText) return setError('Enable text removal or people blurring before processing.')
    setBusy(true)
    setError('')
    setOutBlob(null)
    countdown.start()
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('blur_people', String(blurPeople))
      form.append('remove_text', String(removeText))
      form.append('detect_bodies', String(detectBodies))
      form.append('blur_strength', String(blurStrength))
      const res = await fetch(`${API_BASE}/process`, { method: 'POST', body: form, credentials: 'include' })
      if (!res.ok) {
        const text = await res.text()
        if (res.status === 401) onUnauthorized?.()
        throw new Error(`Server error (${res.status}): ${text.slice(0, 200)}`)
      }
      const blob = await res.blob()
      const nextUploadCount = Number(res.headers.get('X-IP-Upload-Count') || 0)
      setOutBlob(blob)
      setIpUploadCount(nextUploadCount)
      setSkipUploadValidations((res.headers.get('X-Skip-Upload-Validations') || '').toLowerCase() === 'true' || nextUploadCount >= VALIDATION_SKIP_THRESHOLD)
      countdown.complete()
    } catch (error) {
      setError(error?.message || 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  function onReset() {
    clearAll()
  }

  function resetSelection() {
    setFile(null)
    setFileMeta(null)
    setError('')
    setFileNote('')
    if (inputRef.current) inputRef.current.value = ''
  }

  function rejectSelection(event, message) {
    setFile(null)
    setFileMeta(null)
    setError(message)
    setFileNote('')
    event.target.value = ''
  }

  function clearAll() {
    resetSelection()
    setOutBlob(null)
  }

  return {
    blurPeople, blurStrength, busy, countdownMs: countdown.countdownMs, detectBodies, error, file, fileMeta, fileNote, inputRef, lastScrubMs: countdown.lastDurationMs, onFileChange, onProcess, onReset, outBlob, removeText, scrubEtaMs: countdown.etaMs, setBlurPeople, setBlurStrength, setDetectBodies, setError, setFileNote, setOutBlob, setRemoveText,
    clearAll,
    acceptedImageLabel: ACCEPTED_IMAGE_LABEL,
  }
}
