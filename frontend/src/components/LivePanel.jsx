export default function LivePanel(props) {
  const { isAuthenticated, liveActive, liveBusy, liveError, liveFrameUrl, liveIntervalMs, liveJpegQuality, liveMaxDimension, liveStats, liveStatus, liveSupported, setLiveIntervalMs, setLiveJpegQuality, setLiveMaxDimension, startLiveSession, stopLiveSession, videoRef, captureCanvasRef } = props

  return (
    <div className="livePanel">
      <div className="liveHeader">
        <div>
          <div className="liveTitle">Live Webcam Scrub</div>
          <div className="small">Uses the dedicated <code>/process/live</code> endpoint with resized JPEG frames for lower latency than the full-resolution upload API.</div>
        </div>
        <div className="liveButtons">
          <button type="button" onClick={startLiveSession} disabled={!isAuthenticated || liveActive || !liveSupported}>Start live</button>
          <button type="button" className="secondaryButton" onClick={stopLiveSession} disabled={!liveActive && !liveBusy}>Stop</button>
        </div>
      </div>
      <div className="liveControls">
        <label><div className="kv"><strong>Live size</strong><span>{liveMaxDimension}px</span></div><input type="range" min="160" max="1280" step="80" value={liveMaxDimension} onChange={(event) => setLiveMaxDimension(Number(event.target.value))} disabled={liveActive} className="rangeInput" /></label>
        <label><div className="kv"><strong>JPEG quality</strong><span>{liveJpegQuality}</span></div><input type="range" min="40" max="95" step="1" value={liveJpegQuality} onChange={(event) => setLiveJpegQuality(Number(event.target.value))} disabled={liveActive} className="rangeInput" /></label>
        <label><div className="kv"><strong>Frame interval</strong><span>{liveIntervalMs}ms</span></div><input type="range" min="120" max="900" step="30" value={liveIntervalMs} onChange={(event) => setLiveIntervalMs(Number(event.target.value))} disabled={liveActive} className="rangeInput" /></label>
      </div>
      <div className="small">Status: <strong>{liveStatus}</strong>{liveStats ? ` • ${liveStats.sentWidth}x${liveStats.sentHeight} • ${liveStats.latencyMs}ms end-to-end` : ''}</div>
      {liveError ? <div className="errorText">{liveError}</div> : null}
      <div className="liveGrid">
        <div><div className="small previewLabel">Camera input</div><video ref={videoRef} className="preview liveVideo" muted playsInline autoPlay /></div>
        <div><div className="small previewLabel">Scrubbed output</div>{liveFrameUrl ? <img className="preview liveVideo" src={liveFrameUrl} alt="live scrub preview" /> : <div className="small">No live output yet.</div>}</div>
      </div>
      <canvas ref={captureCanvasRef} className="hiddenCanvas" />
    </div>
  )
}
