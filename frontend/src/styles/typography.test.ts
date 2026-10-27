import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const packageJson = JSON.parse(readFileSync(new URL('../../package.json', import.meta.url), 'utf8'))
const entrySource = readFileSync(new URL('../main.ts', import.meta.url), 'utf8')

describe('authentication typography', () => {
  it('bundles and imports the IBM Plex Sans variable font', () => {
    expect(packageJson.dependencies).toHaveProperty('@fontsource-variable/ibm-plex-sans')
    expect(entrySource).toContain("import '@fontsource-variable/ibm-plex-sans/index.css'")
  })
})
