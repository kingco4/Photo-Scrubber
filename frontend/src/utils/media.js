export function blobToUrl(blob) {
  return URL.createObjectURL(blob)
}

export function canvasToBlob(canvas, type, quality) {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (!blob) {
        reject(new Error('Unable to capture webcam frame.'))
        return
      }
      resolve(blob)
    }, type, quality)
  })
}

export function formatCountdown(ms) {
  return `${Math.max(0, Math.ceil(ms / 1000))}s`
}
