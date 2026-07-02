import { useEffect, useState } from 'react'

import { API_BASE } from '../constants'
import { validateLoginFields } from '../utils/fileValidation'

export function useAuthSession({ onUnauthorized }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [accessCode, setAccessCode] = useState('')
  const [requiresAccessCode, setRequiresAccessCode] = useState(false)
  const [authBusy, setAuthBusy] = useState(false)
  const [authError, setAuthError] = useState('')
  const [sessionUser, setSessionUser] = useState('')
  const [ipUploadCount, setIpUploadCount] = useState(0)
  const [skipUploadValidations, setSkipUploadValidations] = useState(false)

  useEffect(() => {
    let cancelled = false
    fetch(`${API_BASE}/auth/settings`).then((res) => (res.ok ? res.json() : null)).then((data) => {
      if (!cancelled) setRequiresAccessCode(Boolean(data?.requires_access_code))
    }).catch(() => {
      if (!cancelled) setRequiresAccessCode(false)
    })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    fetch(`${API_BASE}/auth/me`, { credentials: 'include' }).then(async (res) => {
      if (res.status === 401) {
        if (!cancelled) resetSession()
        return
      }
      if (!res.ok) throw new Error('Unable to restore session')
      const data = await res.json()
      if (!cancelled) applySessionData(data)
    }).catch((error) => {
      if (!cancelled) {
        resetSession()
        setAuthError(error?.message || 'Unable to restore session')
        onUnauthorized?.()
      }
    })
    return () => {
      cancelled = true
    }
  }, [authBusy])

  function applySessionData(data) {
    setIsAuthenticated(true)
    setSessionUser(data.username || '')
    setIpUploadCount(Number(data.ip_upload_count || 0))
    setSkipUploadValidations(Boolean(data.skip_upload_validations))
    setAuthError('')
  }

  function resetSession() {
    setIsAuthenticated(false)
    setSessionUser('')
    setIpUploadCount(0)
    setSkipUploadValidations(false)
  }

  async function login(event) {
    event.preventDefault()
    const validationError = validateLoginFields(username, password, requiresAccessCode, accessCode)
    if (validationError) return setAuthError(validationError)
    setAuthBusy(true)
    setAuthError('')
    try {
      const form = new FormData()
      form.append('username', username.trim())
      form.append('password', password)
      if (requiresAccessCode) form.append('access_code', accessCode.trim())
      const res = await fetch(`${API_BASE}/auth/login`, { method: 'POST', body: form, credentials: 'include' })
      if (!res.ok) {
        const data = await res.json().catch(() => null)
        throw new Error(data?.detail || 'Login failed')
      }
      applySessionData(await res.json())
      setPassword('')
      setAccessCode('')
    } catch (error) {
      setAuthError(error?.message || 'Login failed')
    } finally {
      setAuthBusy(false)
    }
  }

  async function logout() {
    if (isAuthenticated) {
      try {
        await fetch(`${API_BASE}/auth/logout`, { method: 'POST', credentials: 'include' })
      } catch {}
    }
    resetSession()
    setPassword('')
    setAccessCode('')
    onUnauthorized?.()
  }

  return {
    accessCode, authBusy, authError, ipUploadCount, isAuthenticated, login, logout, password, requiresAccessCode, sessionUser, setAccessCode, setAuthError, setIpUploadCount, setPassword, setSkipUploadValidations, setUsername, skipUploadValidations, username,
    resetSession,
  }
}
