#!/usr/bin/env node
import { spawn } from 'child_process';

console.log('Starting ML Experiment Tracker (Backend Only)...');

// Start FastAPI backend
console.log('Starting FastAPI backend on port 8000...');
const backend = spawn('python', ['run_backend.py'], {
  stdio: 'inherit',
  env: { ...process.env, BACKEND_PORT: '8000' }
});

console.log('');
console.log('🚀 FastAPI backend will be available on http://localhost:8000');
console.log('🌐 Start the frontend separately with: pnpm dev');
console.log('   Frontend will be available on http://localhost:5173');
console.log('');

backend.on('error', (err) => {
  console.error('Backend error:', err);
});

backend.on('exit', (code) => {
  console.log(`Backend exited with code ${code}`);
  process.exit(code || 0);
});

// Handle shutdown
process.on('SIGINT', () => {
  console.log('Shutting down backend...');
  backend.kill();
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('Shutting down backend...');
  backend.kill();
  process.exit(0);
});
