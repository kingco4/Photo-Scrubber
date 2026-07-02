import React, { useEffect } from 'react'

import AuthPanel from './components/AuthPanel'
import LivePanel from './components/LivePanel'
import PreviewPanel from './components/PreviewPanel'
import UploadPanel from './components/UploadPanel'
import { useAuthSession } from './hooks/useAuthSession'
import { useLiveScrubber } from './hooks/useLiveScrubber'
import { useObjectUrl } from './hooks/useObjectUrl'
import { usePhotoScrubber } from './hooks/usePhotoScrubber'

export default function App() {
  const auth = useAuthSession()
  const handleUnauthorized = () => {
    auth.resetSession()
    auth.setAuthError('')
  }
  const scrubber = usePhotoScrubber({
    isAuthenticated: auth.isAuthenticated,
    onUnauthorized: handleUnauthorized,
    setIpUploadCount: auth.setIpUploadCount,
    setSkipUploadValidations: auth.setSkipUploadValidations,
    skipUploadValidations: auth.skipUploadValidations,
  })
  const live = useLiveScrubber({
    blurPeople: scrubber.blurPeople,
    blurStrength: scrubber.blurStrength,
    detectBodies: scrubber.detectBodies,
    isAuthenticated: auth.isAuthenticated,
    onUnauthorized: () => {
      handleUnauthorized()
      live.stopLiveSession()
    },
    removeText: scrubber.removeText,
  })
  const inUrl = useObjectUrl(scrubber.file)
  const outUrl = useObjectUrl(scrubber.outBlob)

  useEffect(() => {
    if (!auth.isAuthenticated) {
      live.stopLiveSession()
      scrubber.clearAll()
    }
  }, [auth.isAuthenticated])

  async function handleLogout() {
    live.stopLiveSession()
    scrubber.clearAll()
    await auth.logout()
  }

  return (
    <div className="container">
      <div className="card">
        <div className="h1">Photo Scubber</div>
        <p className="p">Upload a photo, or scrub frames from your webcam live. The upload path stays lossless with PNG output; the live path uses smaller JPEG frames for lower latency.</p>
        <AuthPanel {...auth} busy={scrubber.busy} liveBusy={live.liveBusy} onLogin={auth.login} onLogout={handleLogout} uploadCount={auth.ipUploadCount} />
        {auth.authError ? <div className="errorText authError">{auth.authError}</div> : null}
        <div className="row">
          <UploadPanel {...scrubber} isAuthenticated={auth.isAuthenticated} outUrl={outUrl} />
          <PreviewPanel inUrl={inUrl} outBlob={scrubber.outBlob} outUrl={outUrl} />
        </div>
        <LivePanel {...live} isAuthenticated={auth.isAuthenticated} />
      </div>
      <p className="small footerNote">Notes: Text removal uses Tesseract OCR bounding boxes + OpenCV inpainting. People blurring uses a face detector and optional HOG person detector.</p>
    </div>
  )
}
