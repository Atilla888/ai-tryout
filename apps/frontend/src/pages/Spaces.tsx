import { useParams } from 'react-router-dom'

function Spaces() {
  const { spaceId } = useParams()
  return <h1>Space: {spaceId}</h1>
}

export default Spaces