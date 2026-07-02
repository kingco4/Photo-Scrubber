export const FILE_TYPE_SPECS = [
  { contentType: 'image/jpeg', extensions: ['.jpg', '.jpeg'], aliases: ['image/jpg', 'image/pjpeg'], label: 'JPG' },
  { contentType: 'image/png', extensions: ['.png'], aliases: [], label: 'PNG' },
  { contentType: 'image/webp', extensions: ['.webp'], aliases: [], label: 'WebP' },
  { contentType: 'image/heic', extensions: ['.heic'], aliases: [], label: 'HEIC' },
  { contentType: 'image/heif', extensions: ['.heif'], aliases: [], label: 'HEIF' },
]

export const PRIMARY_FILE_TYPES = FILE_TYPE_SPECS.map((spec) => spec.contentType)
export const FILE_TYPE_TO_EXTENSIONS = Object.fromEntries(
  FILE_TYPE_SPECS.flatMap((spec) => [spec.contentType, ...spec.aliases].map((type) => [type, spec.extensions])),
)
export const ALLOWED_EXTENSIONS = FILE_TYPE_SPECS.flatMap((spec) => spec.extensions)
export const ACCEPTED_IMAGE_LABEL = FILE_TYPE_SPECS.map((spec) => spec.label).join(', ')
export const FILE_INPUT_ACCEPT = [...PRIMARY_FILE_TYPES, ...ALLOWED_EXTENSIONS].join(',')
export const HEIF_FAMILY_TYPES = FILE_TYPE_SPECS.filter((spec) => ['HEIC', 'HEIF'].includes(spec.label)).flatMap((spec) => [spec.contentType, ...spec.extensions])

export function isHeifFamilyFile(file) {
  const lowerName = (file?.name || '').toLowerCase()
  const lowerType = (file?.type || '').toLowerCase()
  return HEIF_FAMILY_TYPES.some((value) => lowerName.endsWith(value) || lowerType === value)
}
