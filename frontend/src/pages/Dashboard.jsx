import { useEffect, useState } from 'react'
import { getJobs, deleteJob, refreshJobs } from '../api/client'
import { JobCard } from '../components/JobCard'

export function Dashboard() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)

  const load = () => {
    setLoading(true)
    getJobs().then(setJobs).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleDelete = (id) => {
    deleteJob(id).then(() => setJobs(js => js.filter(j => j.id !== id)))
  }

  const handleRefresh = () => {
    refreshJobs().then(load)
  }

  if (loading) return <p>Loading jobs...</p>

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>Job Dashboard</h1>
        <button onClick={handleRefresh}>Refresh Now</button>
      </div>
      {jobs.length === 0
        ? <p>No jobs found. Configure your preferences and refresh to discover jobs.</p>
        : jobs.map(job => <JobCard key={job.id} job={job} onDelete={handleDelete} />)
      }
    </div>
  )
}
