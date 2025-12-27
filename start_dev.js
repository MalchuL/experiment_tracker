#!/usr/bin/env node
import { spawn } from 'child_process';

console.log('Starting ML Experiment Tracker...');

// Start FastAPI backend
console.log('Starting FastAPI backend on port 8000...');
const backend = spawn('python', ['run_backend.py'], {
  stdio: 'inherit',
  env: { ...process.env, BACKEND_PORT: '8000' }
});

// Wait 2 seconds for FastAPI to start, then start Express
setTimeout(() => {
  console.log('Starting Express frontend on port 5000...');
  const frontend = spawn('npx', ['tsx', 'server/index.ts'], {
    stdio: 'inherit',
    env: { ...process.env, NODE_ENV: 'development', PORT: '5000' }
  });

  frontend.on('error', (err) => {
    console.error('Frontend error:', err);
  });

  frontend.on('exit', (code) => {
    console.log(`Frontend exited with code ${code}`);
    backend.kill();
    process.exit(code || 0);
  });
}, 2000);

backend.on('error', (err) => {
  console.error('Backend error:', err);
});

backend.on('exit', (code) => {
  console.log(`Backend exited with code ${code}`);
  process.exit(code || 0);
});

// Handle shutdown
process.on('SIGINT', () => {
  console.log('Shutting down...');
  backend.kill();
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('Shutting down...');
  backend.kill();
  process.exit(0);
});
