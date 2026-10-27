import { describe, expect, it, vi } from 'vitest'
import { bootstrap } from './bootstrap'

describe('bootstrap', () => {
  it('restores the session and waits for routing before mounting', async () => {
    const order: string[] = []
    const restoreSession = vi.fn(async () => { order.push('restore') })
    const isReady = vi.fn(async () => { order.push('ready') })
    const mount = vi.fn(() => { order.push('mount') })

    await bootstrap({ restoreSession, isReady, mount })

    expect(order).toEqual(['restore', 'ready', 'mount'])
  })

  it('reports restoration errors but still waits for routing and mounts', async () => {
    const failure = new Error('restore failed')
    const reportError = vi.fn()
    const mount = vi.fn()
    await bootstrap({ restoreSession: vi.fn().mockRejectedValue(failure), isReady: vi.fn(), mount, reportError })
    expect(reportError).toHaveBeenCalledWith(failure)
    expect(mount).toHaveBeenCalledOnce()
  })
})
