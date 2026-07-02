import { MAX_IMAGE_HEIGHT, MAX_IMAGE_WIDTH, MAX_UPLOAD_BYTES, MIN_IMAGE_HEIGHT, MIN_IMAGE_WIDTH } from '../constants'
import { ACCEPTED_IMAGE_LABEL, ALLOWED_EXTENSIONS, FILE_TYPE_TO_EXTENSIONS } from '../fileTypes'

export function validateLoginFields(username, password, requiresAccessCode, accessCode) {
  const normalizedUsername = username.trim()
  if (normalizedUsername.length === 0) return 'Username is required.'
  if (normalizedUsername.length > 256) return 'Username must be at most 256 characters.'
  if (password.length === 0) return 'Password is required.'
  if (password.length > 256) return 'Password must be at most 256 characters.'
  if (requiresAccessCode && accessCode.trim().length === 0) return 'Access code is required.'
  if (accessCode.length > 64) return 'Access code must be at most 64 characters.'
  return ''
}

export function validateSelectedFile(file) {
  if (!file) return 'Select an image first.'
  if (file.size > MAX_UPLOAD_BYTES) return 'Image must be 15 MB or smaller.'
  const normalizedName = file.name.trim().split('/').pop()?.split('\\').pop() || ''
  if (normalizedName.length === 0 || normalizedName === '.' || normalizedName === '..') return 'Image file must have a valid filename.'
  if (normalizedName.length > 255) return 'Image filename must be 255 characters or fewer.'
  if ([...normalizedName].some((char) => char.charCodeAt(0) < 32)) return 'Image filename contains unsupported characters.'
  const lowerName = normalizedName.toLowerCase()
  const matchingExtension = ALLOWED_EXTENSIONS.find((ext) => lowerName.endsWith(ext))
  if (!matchingExtension) return `Use a ${ACCEPTED_IMAGE_LABEL} image.`
  const normalizedType = (file.type || '').toLowerCase()
  const hasKnownButGenericType = normalizedType === '' || normalizedType === 'application/octet-stream'
  if (!hasKnownButGenericType && normalizedType && !Object.keys(FILE_TYPE_TO_EXTENSIONS).includes(normalizedType)) {
    return `Use a ${ACCEPTED_IMAGE_LABEL} image.`
  }
  if (!hasKnownButGenericType && normalizedType) {
    const allowedExtensions = FILE_TYPE_TO_EXTENSIONS[normalizedType] || []
    if (!allowedExtensions.some((ext) => lowerName.endsWith(ext))) {
      return `Filename extension must match ${normalizedType}.`
    }
  }
  return ''
}

export function validateBlurStrength(value) {
  if (!Number.isInteger(value)) return 'Blur strength must be an integer.'
  if (value < 3 || value > 151) return 'Blur strength must be between 3 and 151.'
  if (value % 2 === 0) return 'Blur strength must be an odd number.'
  return ''
}

export function validateLiveSettings(maxDimension, jpegQuality, intervalMs) {
  if (!Number.isInteger(maxDimension) || maxDimension < 160 || maxDimension > 1920) return 'Live max dimension must be between 160 and 1920.'
  if (!Number.isInteger(jpegQuality) || jpegQuality < 40 || jpegQuality > 95) return 'Live JPEG quality must be between 40 and 95.'
  if (!Number.isInteger(intervalMs) || intervalMs < 120 || intervalMs > 1500) return 'Live frame interval must be between 120ms and 1500ms.'
  return ''
}

export async function readImageDimensions(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      resolve({ width: img.naturalWidth, height: img.naturalHeight })
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('Selected file could not be read as an image.'))
    }
    img.src = url
  })
}

export function validateImageDimensions({ width, height }) {
  if (width < MIN_IMAGE_WIDTH || height < MIN_IMAGE_HEIGHT) return `Image must be at least ${MIN_IMAGE_WIDTH}x${MIN_IMAGE_HEIGHT} pixels.`
  if (width > MAX_IMAGE_WIDTH || height > MAX_IMAGE_HEIGHT) return `Image dimensions must not exceed ${MAX_IMAGE_WIDTH}x${MAX_IMAGE_HEIGHT} pixels.`
  return ''
}
