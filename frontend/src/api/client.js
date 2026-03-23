import axios from 'axios'

export const getJobs = () => axios.get('/jobs').then(r => r.data)
export const getJob = (id) => axios.get(`/jobs/${id}`).then(r => r.data)
export const deleteJob = (id) => axios.delete(`/jobs/${id}`).then(r => r.data)
export const refreshJobs = () => axios.post('/jobs/refresh').then(r => r.data)
export const getPreferences = () => axios.get('/preferences').then(r => r.data)
export const savePreferences = (data) => axios.post('/preferences', data).then(r => r.data)
export const getResume = () => axios.get('/resume').then(r => r.data)
export const uploadResume = (file) => {
  const form = new FormData()
  form.append('file', file)
  return axios.post('/resume', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)
}

export const triggerApply = (jobId) => axios.post('/applications', { job_id: jobId }).then(r => r.data)
export const getApplications = () => axios.get('/applications').then(r => r.data)
export const updateApplication = (id, data) => axios.patch(`/applications/${id}`, data).then(r => r.data)
export const openInBrowser = (appId) => axios.post(`/applications/${appId}/open`).then(r => r.data)

export const triggerOutreach = (jobId) => axios.post('/outreach', { job_id: jobId }).then(r => r.data)
export const getOutreach = () => axios.get('/outreach').then(r => r.data)
export const patchOutreach = (id, data) => axios.patch(`/outreach/${id}`, data).then(r => r.data)
export const sendOutreach = (id) => axios.post(`/outreach/${id}/send`).then(r => r.data)
export const connectEmail = () => axios.post('/auth/email/connect').then(r => r.data)
