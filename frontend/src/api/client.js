import axios from 'axios';

const client = axios.create({
    baseURL: import.meta.env.VITE_API_BASE || 'http://localhost:5000',
    timeout: 15000,
});

client.interceptors.response.use(
  (r) => r,
  (err) => {
    // Bubble concise error
    const msg = err?.response?.data?.message || err.message || "Network error";
    return Promise.reject(new Error(msg));
  }
);

export default client;