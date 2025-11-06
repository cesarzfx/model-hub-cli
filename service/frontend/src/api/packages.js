// service/frontend/src/api/packages.js
import apiClient from './client';

export const listPackages = async (params = {}) => {
  const response = await apiClient.get('/v1/packages', { params });
  return response.data;
};

export const getPackage = async (id) => {
  const response = await apiClient.get(`/v1/packages/${id}`);
  return response.data;
};

export const createPackage = async (data) => {
  const response = await apiClient.post('/v1/packages', data);
  return response.data;
};

export const submitCLI = async (data) => {
  const response = await apiClient.post('/v1/ingest/cli', data);
  return response.data;
};

export const ratePackage = async (id) => {
  const response = await apiClient.post(`/v1/rate/${id}`);
  return response.data;
};

export const getNDJSON = async (id) => {
  const response = await apiClient.get(`/v1/rate/${id}/ndjson`);
  return response.data;
};

