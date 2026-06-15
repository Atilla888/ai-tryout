import { useState } from 'react'
import type { Artifact } from '../api/api'
import { artifactDownloadUrl, artifactPreviewUrl } from '../api/api'
import './ArtifactViewer.css'

interface ArtifactViewerProps {
  artifact: Artifact
}

/** Formats an ISO expiration timestamp into a human-readable date/time string. */
function formatExpirationDate(expiresAt: string | null): string {
  if (!expiresAt) return ''
  const date = new Date(expiresAt)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Renders an inline preview for image, audio, or text artifacts. Returns null
 * if the artifact type has no supported preview. */
function renderPreview(artifact: Artifact) {
  const previewUrl = artifactPreviewUrl(artifact.id)

  if (artifact.artifact_type === 'output_image') {
    return (
      <div className="artifact-preview artifact-image-preview">
        <img src={previewUrl} alt={artifact.file_name} />
      </div>
    )
  }

  if (artifact.artifact_type === 'output_audio') {
    return (
      <div className="artifact-preview artifact-audio-preview">
        <audio controls>
          <source src={previewUrl} type={artifact.content_type} />
          Your browser does not support the audio element.
        </audio>
      </div>
    )
  }

  if (artifact.artifact_type === 'output_text') {
    return (
      <TextPreview previewUrl={previewUrl} />
    )
  }

  return null
}

/** Fetches and renders the raw text content of a text artifact.
 * The fetch is triggered inside render rather than useEffect to avoid an extra render cycle. */
function TextPreview({ previewUrl }: { previewUrl: string }) {
  const [content, setContent] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  if (content === null && loading) {
    fetch(previewUrl)
      .then((res) => {
        if (!res.ok) throw new Error('Failed to load text preview')
        return res.text()
      })
      .then((text) => {
        setContent(text)
        setLoading(false)
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load preview')
        setLoading(false)
      })
  }

  if (loading) {
    return (
      <div className="artifact-preview artifact-text-preview">
        <p className="artifact-loading">Loading preview...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="artifact-preview artifact-text-preview">
        <p className="artifact-error">Error: {error}</p>
      </div>
    )
  }

  return (
    <div className="artifact-preview artifact-text-preview">
      <pre>{content}</pre>
    </div>
  )
}

/** Displays an artifact with an optional inline preview and a download button.
 * The download is done client-side via Blob URL to force a Save-As dialog. */
export function ArtifactViewer({ artifact }: ArtifactViewerProps) {
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)

  async function handleDownload() {
    try {
      setDownloading(true)
      setDownloadError(null)
      const url = artifactDownloadUrl(artifact.id)
      const response = await fetch(url)
      if (!response.ok) {
        throw new Error(`Download failed: ${response.statusText}`)
      }
      const blob = await response.blob()
      const downloadUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = artifact.file_name
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(downloadUrl)
    } catch (err) {
      setDownloadError(err instanceof Error ? err.message : 'Download failed')
    } finally {
      setDownloading(false)
    }
  }

  const preview = artifact.preview_supported ? renderPreview(artifact) : null
  const hasPreview = preview !== null
  const expiresAt = artifact.expires_at ? formatExpirationDate(artifact.expires_at) : null

  return (
    <div className="artifact-viewer">
      <div className="artifact-header">
        <h3 className="artifact-name">{artifact.file_name}</h3>
        <button
          className="artifact-download-btn"
          onClick={handleDownload}
          disabled={downloading}
        >
          {downloading ? 'Downloading...' : 'Download'}
        </button>
      </div>

      {expiresAt && (
        <p className="artifact-expiration">Result expires on {expiresAt}</p>
      )}

      {hasPreview && preview}

      {!hasPreview && (
        <div className="artifact-no-preview">
          <p>Preview not available for this file type.</p>
        </div>
      )}

      {downloadError && (
        <p className="artifact-error">Error: {downloadError}</p>
      )}
    </div>
  )
}

export default ArtifactViewer
