import { execFileSync } from 'node:child_process'
import { randomBytes } from 'node:crypto'
import path from 'node:path'
import { fileURLToPath } from 'node:url'


export default function globalSetup() {
  const e2eDir = path.dirname(fileURLToPath(import.meta.url))
  const backendDir = path.resolve(e2eDir, '..', '..', 'backend')
  const python = path.join(backendDir, '.venv', 'Scripts', 'python.exe')
  process.env.XZX_E2E_ADMIN_EMAIL = 'stage5-admin@example.com'
  process.env.XZX_E2E_ADMIN_PASSWORD = `Stage5!${randomBytes(12).toString('hex')}Aa1`
  const env = {
    ...process.env,
    DATABASE_URL: process.env.XZX_E2E_DATABASE_URL,
    XZX_ADMIN_PASSWORD: process.env.XZX_E2E_ADMIN_PASSWORD,
  }
  execFileSync(python, ['-m', 'alembic', 'upgrade', 'head'], {
    cwd: backendDir,
    env,
    stdio: 'pipe',
  })
  execFileSync(
    python,
    [
      '-m',
      'scripts.bootstrap_admin',
      '--username',
      'stage5admin',
      '--email',
      process.env.XZX_E2E_ADMIN_EMAIL,
      '--non-interactive',
    ],
    { cwd: backendDir, env, stdio: 'pipe' },
  )
}
