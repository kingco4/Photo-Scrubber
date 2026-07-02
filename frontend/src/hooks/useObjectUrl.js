import { useEffect, useState } from 'react'

export function useObjectUrl(source, createUrl = URL.createObjectURL) {
  const [url, setUrl] = useState('')

  useEffect(() => {
    if (!source) {
      setUrl('')
      return
    }
    const nextUrl = createUrl(source)
    setUrl(nextUrl)
    return () => {
      URL.revokeObjectURL(nextUrl)
    }
  }, [source, createUrl])

  return url
}
