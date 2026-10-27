import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('Vercel deployment', () => {
  it('serves the Vue entrypoint for direct SPA route requests', () => {
    const manifest = JSON.parse(
      readFileSync(resolve(process.cwd(), 'vercel.json'), 'utf8'),
    ) as { rewrites?: Array<{ source: string; destination: string }> }

    expect(manifest.rewrites).toContainEqual({
      source: '/(.*)',
      destination: '/index.html',
    })
  })
})
