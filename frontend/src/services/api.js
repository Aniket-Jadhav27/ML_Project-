import axios from 'axios';

const API_BASE_URL = 'http://localhost:8080/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach JWT token automatically
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('rag_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to catch 401 unauthenticated
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Clear token if invalid
      localStorage.removeItem('rag_token');
      localStorage.removeItem('rag_user');
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  register: async (username, email, password) => {
    const res = await api.post('/auth/register', { username, email, password });
    return res.data;
  },
  login: async (username, password) => {
    const res = await api.post('/auth/login', { username, password });
    return res.data;
  },
  getCurrentUser: async () => {
    const res = await api.get('/auth/me');
    return res.data;
  },
};

export const chatAPI = {
  ask: async (question) => {
    const res = await api.post('/chat/ask', { question });
    return res.data;
  },
  getHistory: async () => {
    const res = await api.get('/chat/history');
    return res.data;
  },
  deleteHistoryItem: async (id) => {
    const res = await api.delete(`/chat/history/${id}`);
    return res.data;
  },
  clearHistory: async () => {
    const res = await api.delete('/chat/history/clear');
    return res.data;
  },
};

export const documentAPI = {
  upload: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await api.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },
  getChunks: async () => {
    const res = await api.get('/documents/chunks');
    return res.data;
  },
  getList: async () => {
    const res = await api.get('/documents/list');
    return res.data;
  },
  getStructure: async () => {
    const res = await api.get('/documents/structure');
    return res.data;
  },
  getTables: async () => {
    const res = await api.get('/documents/tables');
    return res.data;
  },
};

export default api;

