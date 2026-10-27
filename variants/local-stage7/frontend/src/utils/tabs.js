export function handleTabKeydown(event, index, items, select) {
  const targets = {
    ArrowLeft: (index - 1 + items.length) % items.length,
    ArrowRight: (index + 1) % items.length,
    Home: 0,
    End: items.length - 1,
  }
  const nextIndex = targets[event.key]
  if (nextIndex === undefined) return

  event.preventDefault()
  select(items[nextIndex].value)
  const tablist = event.currentTarget.closest('[role="tablist"]')
  tablist?.querySelectorAll('[role="tab"]')[nextIndex]?.focus()
}
