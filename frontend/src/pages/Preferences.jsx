import { useEffect, useState } from 'react'
import { getPreferences, savePreferences, uploadResume, getResume } from '../api/client'
import { TagInput } from '../components/TagInput'
import '../components/Form.css'

const EXPERIENCE_OPTIONS = [
  { value: 'associate',       label: 'Associate'        },
  { value: 'mid-level',       label: 'Mid-level'        },
  { value: 'senior-level',    label: 'Senior-level'     },
  { value: 'executive-level', label: 'Executive-level'  },
]

const DOMAIN_OPTIONS = [
  { value: 'backend',           label: 'Backend Engineering'    },
  { value: 'frontend',          label: 'Frontend Engineering'   },
  { value: 'full-stack',        label: 'Full Stack'             },
  { value: 'data-science',      label: 'Data Science'           },
  { value: 'ml-ai',             label: 'ML / AI'                },
  { value: 'devops-infra',      label: 'DevOps / Infrastructure'},
  { value: 'mobile',            label: 'Mobile (iOS/Android)'   },
  { value: 'security',          label: 'Security'               },
  { value: 'data-engineering',  label: 'Data Engineering'       },
  { value: 'sre-platform',      label: 'SRE / Platform'         },
  { value: 'product-management',label: 'Product Management'     },
  { value: 'design-ux',         label: 'Design / UX'            },
  { value: 'qa-testing',        label: 'QA / Testing'           },
  { value: 'game-development',  label: 'Game Development'       },
  { value: 'blockchain-web3',   label: 'Blockchain / Web3'      },
  { value: 'embedded-systems',      label: 'Embedded Systems'         },
  { value: 'professional-services', label: 'Professional Services'    },
]

const INDUSTRY_OPTIONS = [
  { value: 'technology',           label: 'Technology'                   },
  { value: 'finance-banking',      label: 'Finance & Banking'            },
  { value: 'healthcare',           label: 'Healthcare & Life Sciences'   },
  { value: 'education',            label: 'Education'                    },
  { value: 'retail-ecommerce',     label: 'Retail & E-commerce'          },
  { value: 'manufacturing',        label: 'Manufacturing'                },
  { value: 'media-entertainment',  label: 'Media & Entertainment'        },
  { value: 'government',           label: 'Government & Public Sector'   },
  { value: 'consulting',           label: 'Consulting'                   },
  { value: 'real-estate',          label: 'Real Estate'                  },
  { value: 'energy-utilities',     label: 'Energy & Utilities'           },
  { value: 'logistics',            label: 'Transportation & Logistics'   },
  { value: 'telecom',              label: 'Telecommunications'           },
  { value: 'legal',                label: 'Legal Services'               },
  { value: 'nonprofit',            label: 'Non-Profit'                   },
  { value: 'automotive',           label: 'Automotive'                   },
  { value: 'aerospace-defense',    label: 'Aerospace & Defense'          },
  { value: 'food-beverage',        label: 'Food & Beverage'              },
  { value: 'hospitality-travel',   label: 'Hospitality & Travel'         },
  { value: 'insurance',            label: 'Insurance'                    },
  { value: 'agriculture',          label: 'Agriculture'                  },
  { value: 'construction',         label: 'Construction & Engineering'   },
]

const COMPANY_SIZE_OPTIONS = [
  { value: '<50',       label: '< 50'         },
  { value: '50-200',    label: '50 – 200'     },
  { value: '200-500',   label: '200 – 500'    },
  { value: '500-1000',  label: '500 – 1,000'  },
  { value: '1000-5000', label: '1,000 – 5,000'},
  { value: '5000+',     label: '5,000+'       },
]

export function Preferences() {
  const [form, setForm] = useState({
    job_titles: [],
    location: 'India',
    remote_hybrid: 'any',
    experience_level: '',
    domain: '',
    company_size: [],
    industry: [],
  })
  const [resume, setResume] = useState(null)
  const [saved, setSaved] = useState(false)
  const [resumeError, setResumeError] = useState('')

  useEffect(() => {
    getPreferences().then(pref => {
      if (pref) setForm({
        job_titles: pref.job_titles || [],
        location: 'India',
        remote_hybrid: pref.remote_hybrid || 'any',
        experience_level: pref.experience_level || '',
        domain: pref.domain || '',
        company_size: pref.company_size || [],
        industry: pref.industry || [],
      })
    })
    getResume().then(setResume)
  }, [])

  const set = (key) => (e) => setForm(f => ({ ...f, [key]: e.target.value }))

  const toggleSize = (value) => {
    setForm(f => ({
      ...f,
      company_size: f.company_size.includes(value)
        ? f.company_size.filter(v => v !== value)
        : [...f.company_size, value],
    }))
  }

  const toggleIndustry = (value) => {
    setForm(f => ({
      ...f,
      industry: f.industry.includes(value)
        ? f.industry.filter(v => v !== value)
        : [...f.industry, value],
    }))
  }

  const handleSave = (e) => {
    e.preventDefault()
    savePreferences(form).then(() => setSaved(true))
  }

  const handleResumeUpload = (e) => {
    const file = e.target.files[0]
    if (!file) return
    if (file.type !== 'application/pdf') {
      setResumeError('Only PDF files are accepted.')
      return
    }
    if (file.size > 50 * 1024 * 1024) {
      setResumeError('File exceeds the 50 MB size limit.')
      return
    }
    setResumeError('')
    uploadResume(file).then(setResume)
  }

  return (
    <div>
      <h2 style={{ color: 'var(--text-primary)', marginBottom: 4 }}>Preferences</h2>
      <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 24 }}>
        Configure your job search criteria
      </p>

      <form onSubmit={handleSave}>
        <div className="form-section">
          <div className="form-section-title">Search Criteria</div>

          <div className="field" style={{ marginBottom: 16 }}>
            <label htmlFor="job_titles">Job Titles</label>
            <TagInput
              id="job_titles"
              values={form.job_titles}
              onChange={(vals) => setForm(f => ({ ...f, job_titles: vals }))}
              placeholder="Add title, press Enter"
            />
            <span className="field-hint">Press Enter or comma to add · click × to remove</span>
          </div>

          <div className="form-row">
            <div className="field">
              <label htmlFor="location">Location</label>
              <div id="location" className="input" style={{ color: 'var(--text-muted)', userSelect: 'none' }}>
                Only Indian Metro cities
              </div>
            </div>
            <div className="field">
              <label htmlFor="remote_hybrid">Arrangement</label>
              <select
                id="remote_hybrid"
                className="select"
                value={form.remote_hybrid}
                onChange={set('remote_hybrid')}
              >
                <option value="any">Any</option>
                <option value="remote">Remote</option>
                <option value="hybrid">Hybrid</option>
                <option value="onsite">Onsite</option>
              </select>
            </div>
          </div>

          <div className="form-row">
            <div className="field">
              <label htmlFor="experience_level">Experience Level</label>
              <select
                id="experience_level"
                className="select"
                value={form.experience_level}
                onChange={set('experience_level')}
              >
                <option value="">Select level…</option>
                {EXPERIENCE_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="domain">Domain</label>
              <select
                id="domain"
                className="select"
                value={form.domain}
                onChange={set('domain')}
              >
                <option value="">Select domain…</option>
                {DOMAIN_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="field" style={{ marginBottom: 16 }}>
            <label>Company Size</label>
            <div className="checkbox-group">
              {COMPANY_SIZE_OPTIONS.map(o => (
                <label key={o.value} className="checkbox-pill">
                  <input
                    type="checkbox"
                    checked={form.company_size.includes(o.value)}
                    onChange={() => toggleSize(o.value)}
                  />
                  {o.label}
                </label>
              ))}
            </div>
          </div>

          <div className="field" style={{ marginBottom: 16 }}>
            <label>Industry Domain</label>
            <div className="checkbox-group" style={{ maxHeight: 160, overflowY: 'auto' }}>
              {INDUSTRY_OPTIONS.map(o => (
                <label key={o.value} className="checkbox-pill">
                  <input
                    type="checkbox"
                    checked={form.industry.includes(o.value)}
                    onChange={() => toggleIndustry(o.value)}
                  />
                  {o.label}
                </label>
              ))}
            </div>
          </div>

        </div>

        <button type="submit" className="btn-primary">Save Preferences</button>
        {saved && (
          <span style={{ color: 'var(--accent)', marginLeft: 12, fontSize: 13 }}>Saved!</span>
        )}
      </form>

      <div className="form-section" style={{ marginTop: 24 }}>
        <div className="form-section-title">Resume</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {resume && (
            <div className="input" style={{ flex: 1 }}>📄 {resume.filename}</div>
          )}
          <label>
            <input
              type="file"
              accept=".pdf,.docx"
              style={{ display: 'none' }}
              onChange={handleResumeUpload}
            />
            <span className="btn-secondary" style={{ cursor: 'pointer' }}>
              {resume ? 'Replace' : 'Upload Resume'}
            </span>
          </label>
        </div>
        {resumeError && (
          <div style={{ color: '#dc2626', fontSize: 12, marginTop: 6 }}>{resumeError}</div>
        )}
      </div>
    </div>
  )
}
