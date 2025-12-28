export const config = {
  API_BASE_URL: process.env.VITE_API_BASE_URL || 'http://localhost:8000',
};

// Debug: log the API base URL
console.log('🔧 API_BASE_URL:', config.API_BASE_URL);
console.log('🔧 VITE_API_BASE_URL env:', process.env.VITE_API_BASE_URL);
