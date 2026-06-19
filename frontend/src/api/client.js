import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('civitech_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      const url = err.config?.url || ''
      // Ne pas rediriger pour les endpoints publics (réactions, média…)
      const isPublicEndpoint = url.includes('/reactions/') || url.includes('/media/')
      if (!isPublicEndpoint) {
        localStorage.removeItem('civitech_token')
        localStorage.removeItem('civitech_user')
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  }
)

export default api

export const authApi = {
  login: (email, password) => {
    const form = new URLSearchParams()
    form.append('username', email)
    form.append('password', password)
    return api.post('/auth/login', form, { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } })
  },
  register: (data) => api.post('/auth/register', data),
  me: () => api.get('/auth/me'),
  updateMe: (data) => api.patch('/auth/me', data),
}

export const publicApi = {
  stats: () => api.get('/public/stats'),
  consultations: () => api.get('/public/consultations'),
  alerts: () => api.get('/public/alerts'),
  sectors: () => api.get('/public/sectors'),
  verifyAmbassador: (code) => api.get(`/public/verify-ambassador/${code}`),
  get: (path, config) => api.get(path, config),
}

export const entitiesApi = {
  list: (params) => api.get('/entities/', { params }),
  get: (slug) => api.get(`/entities/${slug}`),
  create: (data) => api.post('/entities/', data),
  update: (id, data) => api.patch(`/entities/${id}`, data),
  delete: (id) => api.delete(`/entities/${id}`),
  addLink: (id, data) => api.post(`/entities/${id}/links`, data),
}

export const factsApi = {
  list: (params) => api.get('/facts/', { params }),
  pending: () => api.get('/facts/pending'),
  mySubmitted: () => api.get('/facts/my/submitted'),
  get: (slug) => api.get(`/facts/${slug}`),
  create: (data) => api.post('/facts/', data),
  update: (id, data) => api.patch(`/facts/${id}`, data),
  delete: (id) => api.delete(`/facts/${id}`),
  verify: (id, data) => api.patch(`/facts/${id}/verify`, data),
  addSource: (id, data) => api.post(`/facts/${id}/sources`, data),
  addActor: (id, data) => api.post(`/facts/${id}/actors`, data),
}

export const threadsApi = {
  list: (params) => api.get('/threads/', { params }),
  get: (slug) => api.get(`/threads/${slug}`),
  create: (data) => api.post('/threads/', data),
  update: (id, data) => api.patch(`/threads/${id}`, data),
  delete: (id) => api.delete(`/threads/${id}`),
  addFact: (id, data) => api.post(`/threads/${id}/facts`, data),
  removeFact: (threadId, factId) => api.delete(`/threads/${threadId}/facts/${factId}`),
  pending: () => api.get('/threads/pending/list'),
}

export const consultationsApi = {
  list: (status) => api.get('/consultations/', { params: { status } }),
  get: (id) => api.get(`/consultations/${id}`),
  create: (data) => api.post('/consultations/', data),
  respond: (id, answers) => api.post(`/consultations/${id}/respond`, answers),
  updateStatus: (id, status) => api.patch(`/consultations/${id}/status`, null, { params: { new_status: status } }),
  update: (id, data) => api.patch(`/consultations/${id}`, data),
  delete: (id) => api.delete(`/consultations/${id}`),
  // Admin
  adminList: (status) => api.get('/consultations/admin/all', { params: { status } }),
  results: (id) => api.get(`/consultations/${id}/results`),
  // Questions CRUD
  listQuestions: (id) => api.get(`/consultations/${id}/questions`),
  addQuestion: (id, data) => api.post(`/consultations/${id}/questions`, data),
  updateQuestion: (id, qid, data) => api.patch(`/consultations/${id}/questions/${qid}`, data),
  deleteQuestion: (id, qid) => api.delete(`/consultations/${id}/questions/${qid}`),
  // Admin avancé
  exportResponses: (id) => api.get(`/consultations/${id}/export`, { responseType: 'blob' }),
  respondents: (id) => api.get(`/consultations/${id}/respondents`),
  generateInsight: (id, publish = false) => api.post(`/consultations/${id}/insights`, { publish }),
  toggleInsightPublish: (id, publish) => api.patch(`/consultations/${id}/insights/publish`, { publish }),
}

export const alertsApi = {
  create: (data) => api.post('/alerts/', data),
  myAlerts: () => api.get('/alerts/my-alerts'),
  list: (status) => api.get('/alerts/', { params: { status } }),
  review: (id, data) => api.patch(`/alerts/${id}/review`, null, { params: data }),
  delete: (id) => api.delete(`/alerts/${id}`),
}

export const ambassadorsApi = {
  apply: (data) => api.post('/ambassadors/apply', data),
  myProfile: () => api.get('/ambassadors/my-profile'),
  list: (status) => api.get('/ambassadors/', { params: { status } }),
  updateStatus: (id, status, notes) => api.patch(`/ambassadors/${id}/status`, null, { params: { new_status: status, notes } }),
}

export const adminApi = {
  dashboard: () => api.get('/admin/dashboard'),
  users: (role, opts = {}) => api.get('/admin/users', { params: { role, ...opts } }),
  getUser: (id) => api.get(`/admin/users/${id}`),
  createUser: (data) => api.post('/admin/users', data),
  updateUser: (id, data) => api.patch(`/admin/users/${id}`, data),
  deleteUser: (id) => api.delete(`/admin/users/${id}`),
  referredUsers: (id) => api.get(`/admin/users/${id}/referred`),
  auditLogs: (limit) => api.get('/admin/audit-logs', { params: { limit } }),
}

export const aiApi = {
  listProviders: () => api.get('/ai/providers'),
  upsertProvider: (name, data) => api.put(`/ai/providers/${name}`, data),
  deleteProviderKey: (name) => api.delete(`/ai/providers/${name}`),
  testProvider: (name) => api.post(`/ai/providers/${name}/test`),
  insights: (data) => api.post('/ai/insights', data),
  fetchModels: (name) => api.get(`/ai/providers/${name}/models`),
  parseFile: (formData, providerId) => {
    const params = providerId ? { provider_id: providerId } : {}
    return api.post('/ai/ingest/parse', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      params,
    })
  },
  importParsed: (data) => api.post('/ai/ingest/import', data),
  // Templates & Export
  downloadTemplate: (type) =>
    api.get(`/ai/templates/${type}`, { responseType: 'blob' }),
  exportContent: (type, params) =>
    api.get(`/ai/export/${type}`, { params, responseType: 'blob' }),
}

export const reactionsApi = {
  get: (type, id) => api.get(`/reactions/${type}/${id}`),
  react: (type, id, reaction) => api.post(`/reactions/${type}/${id}`, { reaction }),
}

export const uploadApi = {
  avatar: (file) => {
    const fd = new FormData(); fd.append('file', file)
    return api.post('/upload/avatar', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  images: (files, folder = 'content') => {
    const fd = new FormData()
    files.forEach(f => fd.append('files', f))
    return api.post(`/upload/images?folder=${folder}`, fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  documents: (files, folder = 'documents') => {
    const fd = new FormData()
    files.forEach(f => fd.append('files', f))
    return api.post(`/upload/documents?folder=${folder}`, fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
}

export const settingsApi = {
  getPublic: () => api.get('/settings/public'),
  getAll: () => api.get('/settings/'),
  update: (updates) => api.patch('/settings/', updates),
  getSectors: () => api.get('/settings/sectors'),
  updateSector: (id, data) => api.patch(`/settings/sectors/${id}`, data),
  createSector: (data) => api.post('/settings/sectors', data),
}
