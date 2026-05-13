import { useNavigate } from 'react-router-dom'
import type { Space } from '../api/api'
import './SpaceCard.css'

const PILL_CLASS: Record<string, string> = {
  Audio: 'pill-audio',
  Video: 'pill-video',
  '3D': 'pill-3d',
  Image: 'pill-image',
  Text: 'pill-text',
}

interface Props {
  space: Space
}

function SpaceCard({ space }: Props) {
  const navigate = useNavigate()

  const taskClass = PILL_CLASS[space.task_type] ?? 'pill-default'
  const inputs = space.input_types as string[]
  const outputs = space.output_types as string[]

  return (
    <article className="space-card" onClick={() => navigate(`/spaces/${space.id}`)}>
      <div className="sc-name">{space.name}</div>
      {space.description && <div className="sc-desc">{space.description}</div>}

      <div className="sc-badges">
        <span className={`pill ${taskClass}`}>{space.task_type}</span>
        {inputs.map((t) => (
          <span key={`in-${t}`} className={`pill ${PILL_CLASS[t] ?? 'pill-default'}`}>
            {t} in
          </span>
        ))}
        {outputs.map((t) => (
          <span key={`out-${t}`} className={`pill ${PILL_CLASS[t] ?? 'pill-default'}`}>
            {t} out
          </span>
        ))}
      </div>

      <div className="sc-footer">
        <span className="sc-meta">{space.status}</span>
        <button
          className="btn-open"
          onClick={(e) => {
            e.stopPropagation()
            navigate(`/spaces/${space.id}`)
          }}
        >
          Open
        </button>
      </div>
    </article>
  )
}

export default SpaceCard
