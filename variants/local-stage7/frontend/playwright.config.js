import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { defineConfig, devices } from '@playwright/test'


const frontendDir = path.dirname(fileURLToPath(import.meta.url))
const projectRoot = path.resolve(frontendDir, '..')
const backendDir = path.join(projectRoot, 'backend')
const artifactDir = path.join(projectRoot, 'output', 'playwright', 'stage-5')
const runId = `${process.pid}-${Date.now()}`
const databasePath = path.join(artifactDir, `e2e-${runId}.db`).replaceAll('\\', '/')
const databaseUrl = `sqlite:///${databasePath}`

fs.mkdirSync(artifactDir, { recursive: true })
process.env.XZX_E2E_DATABASE_URL = databaseUrl

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 420_000,
  expect: { timeout: 15_000 },
  forbidOnly: true,
  retries: 0,
  outputDir: path.join(artifactDir, 'test-results'),
  reporter: [['line'], ['html', { outputFolder: path.join(artifactDir, 'report'), open: 'never' }]],
  globalSetup: './e2e/global-setup.js',
  use: {
    baseURL: 'http://127.0.0.1:5173',
    channel: 'msedge',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
  },
  projects: [
    {
      name: 'edge',
      use: { ...devices['Desktop Edge'], channel: 'msedge' },
    },
  ],
  webServer: [
    {
      name: 'FastAPI',
      command: '.\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000',
      cwd: backendDir,
      url: 'http://127.0.0.1:8000/api/health',
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: 'pipe',
      stderr: 'pipe',
      env: {
        ...process.env,
        DATABASE_URL: databaseUrl,
        AUTO_CREATE_TABLES: 'false',
        FAISS_INDEX_PATH: path.join(artifactDir, `faiss-${runId}`, 'index.faiss'),
        KNOWLEDGE_UPLOAD_DIR: path.join(artifactDir, `knowledge-${runId}`),
      },
    },
    {
      name: 'Vite',
      command: 'npm run dev -- --host 127.0.0.1 --port 5173 --strictPort',
      cwd: frontendDir,
      url: 'http://127.0.0.1:5173/login',
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: 'pipe',
      stderr: 'pipe',
    },
  ],
})
