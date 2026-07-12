interface BootstrapDependencies {
  restoreSession: () => Promise<void>
  isReady: () => Promise<void>
  mount: () => unknown
  reportError?: (cause: unknown) => void
}

export async function bootstrap({
  restoreSession,
  isReady,
  mount,
  reportError = console.error,
}: BootstrapDependencies): Promise<void> {
  try {
    await restoreSession()
  } catch (cause) {
    reportError(cause)
  }
  await isReady()
  mount()
}
