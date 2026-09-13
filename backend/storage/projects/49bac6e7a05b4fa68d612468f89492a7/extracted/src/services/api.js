import axios from 'axios';

const apiClient = axios.create({
  baseURL: 'https://api.taskflow.dev/v1',
  timeout: 8000,
});

export async function fetchTasks() {
  const response = await apiClient.get('/tasks');
  return response.data;
}

export async function completeTask(taskId) {
  const response = await apiClient.post(`/tasks/${taskId}/complete`);
  return response.data;
}

export async function loginUser(credentials) {
  const response = await apiClient.post('/auth/login', credentials);
  return response.data;
}
