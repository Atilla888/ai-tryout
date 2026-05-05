import { useParams } from 'react-router-dom'

function JobDetail() {
  const { jobId } = useParams()
  return <h1>Job: {jobId}</h1>
}

export default JobDetail