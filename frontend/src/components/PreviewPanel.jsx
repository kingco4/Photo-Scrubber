export default function PreviewPanel({ inUrl, outBlob, outUrl }) {
  return (
    <div className="col">
      <div className="row">
        <div className="col">
          <div className="small previewLabel">Input</div>
          {inUrl ? <img className="preview" src={inUrl} alt="input preview" /> : <div className="small">No image selected.</div>}
        </div>
        <div className="col">
          <div className="small previewLabel">Output</div>
          {outBlob ? <img className="preview" src={outUrl} alt="output preview" /> : <div className="small">No output yet.</div>}
        </div>
      </div>
    </div>
  )
}
