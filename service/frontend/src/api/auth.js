// service/frontend/src/api/auth.js
import apiClient from './client';

export const login = async (username, password) => {
  const response = await apiClient.post('/v1/auth/login', { username, password });
  return response.data;
};

export const whoami = async () => {
  const response = await apiClient.get('/v1/auth/whoami');
  return response.data;
};

