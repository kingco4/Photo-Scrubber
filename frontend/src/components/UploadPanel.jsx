import { API_BASE, VALIDATION_SKIP_THRESHOLD } from '../constants'
import { FILE_INPUT_ACCEPT } from '../fileTypes'
import { formatCountdown } from '../utils/media'

export default function UploadPanel(props) {
  const { acceptedImageLabel, blurPeople, blurStrength, busy, countdownMs, detectBodies, error, file, fileMeta, fileNote, inputRef, isAuthenticated, lastScrubMs, onFileChange, onProcess, onReset, outBlob, outUrl, removeText, scrubEtaMs, setBlurPeople, setBlurStrength, setDetectBodies, setRemoveText } = props

  return (
    <div className="col">
      <div className="controls">
        <label><strong>Image</strong><input ref={inputRef} type="file" accept={FILE_INPUT_ACCEPT} onChange={onFileChange} /></label>
        <label><input type="checkbox" checked={removeText} onChange={(event) => setRemoveText(event.target.checked)} />Remove text</label>
        <label><input type="checkbox" checked={blurPeople} onChange={(event) => setBlurPeople(event.target.checked)} />Blur people</label>
        <label className="indented"><input type="checkbox" checked={detectBodies} onChange={(event) => setDetectBodies(event.target.checked)} disabled={!blurPeople} />Also detect full bodies (slower)</label>
        <label>
          <div className="kv"><strong>Blur</strong><span>{blurStrength}</span></div>
          <input type="range" min="3" max="151" step="2" value={blurStrength} onChange={(event) => setBlurStrength(Number(event.target.value))} disabled={!blurPeople} className="rangeInput" />
        </label>
        {fileMeta ? <div className="small">Selected image: {fileMeta.width}x{fileMeta.height}px, {(file.size / (1024 * 1024)).toFixed(2)} MB</div> : null}
        {fileNote ? <div className="small">{fileNote}</div> : null}
        <div className="row buttonRow">
          <button onClick={onProcess} disabled={!isAuthenticated || !file || busy || (!blurPeople && !removeText)}>{busy ? 'Processing…' : 'Process'}</button>
          <button onClick={onReset} disabled={busy}>Reset</button>
          {outBlob ? <a href={outUrl} download={`scubbed_${file?.name || 'image'}.png`}><button type="button">Download</button></a> : null}
        </div>
        <div className="small">API: <code>{API_BASE}</code> (set <code>VITE_API_BASE</code> to change)</div>
        {busy ? <div className="small">Estimated time remaining: <strong>{formatCountdown(countdownMs)}</strong></div> : null}
        {!busy && lastScrubMs > 0 ? <div className="small">Last scrub took {(lastScrubMs / 1000).toFixed(1)}s. Next estimate: {formatCountdown(scrubEtaMs)}.</div> : null}
        <div className="small">Accepted images: {acceptedImageLabel} up to 15 MB. Browser checks relax after {VALIDATION_SKIP_THRESHOLD} uploads from the same IP.</div>
        {error ? <div className="errorText">{error}</div> : null}
      </div>
    </div>
  )
}
