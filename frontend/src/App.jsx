import React, { useMemo, useRef, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

function blobToUrl(blob) {
  return URL.createObjectURL(blob)
}

export default function App() {
  const [file, setFile] = useState(null)
  const [blurPeople, setBlurPeople] = useState(true)
  const [removeText, setRemoveText] = useState(true)
  const [detectBodies, setDetectBodies] = useState(false)
  const [blurStrength, setBlurStrength] = useState(31)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [outBlob, setOutBlob] = useState(null)

  const inputRef = useRef(null)

  const inUrl = useMemo(() => (file ? URL.createObjectURL(file) : ''), [file])
  const outUrl = useMemo(() => (outBlob ? blobToUrl(outBlob) : ''), [outBlob])

  async function onProcess() {
    if (!file) return
    setBusy(true)
    setError('')
    setOutBlob(null)
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('blur_people', String(blurPeople))
      form.append('remove_text', String(removeText))
      form.append('detect_bodies', String(detectBodies))
      form.append('blur_strength', String(blurStrength))

      const res = await fetch(`${API_BASE}/process`, { method: 'POST', body: form })
      if (!res.ok) {
        const t = await res.text()
        throw new Error(`Server error (${res.status}): ${t.slice(0, 200)}`)
      }
      const blob = await res.blob()
      setOutBlob(blob)
    } catch (e) {
      setError(e?.message || 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  function onReset() {
    setFile(null)
    setOutBlob(null)
    setError('')
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <div className="container">
      <div className="card">
        <div className="h1">Photo Scubber</div>
        <p className="p">
          Upload a photo, then scrub text and/or blur background people. Runs locally using React on the front-end and FastAPI on the back-end.
        </p>

        <div className="row">
          <div className="col">
            <div className="controls">
              <label>
                <strong>Image</strong>
                <input
                  ref={inputRef}
                  type="file"
                  accept="image/*"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                />
              </label>

              <label>
                <input type="checkbox" checked={removeText} onChange={(e) => setRemoveText(e.target.checked)} />
                Remove text
              </label>

              <label>
                <input type="checkbox" checked={blurPeople} onChange={(e) => setBlurPeople(e.target.checked)} />
                Blur people
              </label>

              <label style={{ paddingLeft: 24 }}>
                <input
                  type="checkbox"
                  checked={detectBodies}
                  onChange={(e) => setDetectBodies(e.target.checked)}
                  disabled={!blurPeople}
                />
                Also detect full bodies (slower)
              </label>

              <label>
                <div className="kv">
                  <strong>Blur</strong>
                  <span>{blurStrength}</span>
                </div>
                <input
                  type="range"
                  min="3"
                  max="151"
                  step="2"
                  value={blurStrength}
                  onChange={(e) => setBlurStrength(Number(e.target.value))}
                  disabled={!blurPeople}
                  style={{ width: 220 }}
                />
              </label>

              <div className="row" style={{ gap: 10 }}>
                <button onClick={onProcess} disabled={!file || busy || (!blurPeople && !removeText)}>
                  {busy ? 'Processing…' : 'Process'}
                </button>
                <button onClick={onReset} disabled={busy}>
                  Reset
                </button>
                {outBlob ? (
                  <a href={outUrl} download={`scubbed_${file?.name || 'image'}.png`}>
                    <button type="button">Download</button>
                  </a>
                ) : null}
              </div>

              <div className="small">
                API: <code>{API_BASE}</code> (set <code>VITE_API_BASE</code> to change)
              </div>

              {error ? <div style={{ color: '#b00020' }}>{error}</div> : null}
            </div>
          </div>

          <div className="col">
            <div className="row">
              <div className="col">
                <div className="small" style={{ marginBottom: 6 }}>Input</div>
                {inUrl ? <img className="preview" src={inUrl} alt="input preview" /> : <div className="small">No image selected.</div>}
              </div>
              <div className="col">
                <div className="small" style={{ marginBottom: 6 }}>Output</div>
                {outUrl ? <img className="preview" src={outUrl} alt="output preview" /> : <div className="small">No output yet.</div>}
              </div>
            </div>
          </div>
        </div>
      </div>

      <p className="small" style={{ marginTop: 14 }}>
        Notes: Text removal uses Tesseract OCR bounding boxes + OpenCV inpainting. People blurring uses a face detector and optional HOG person detector.
      </p>
    </div>
  )
}
