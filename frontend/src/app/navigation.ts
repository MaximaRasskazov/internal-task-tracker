export function safeReturn(value: unknown): string {
  if (
    typeof value !== 'string' ||
    !value.startsWith('/') ||
    value.startsWith('//') ||
    /[\\\r\n]/.test(value)
  )
    return '/projects'
  if (/^\/(login|register)([/?#]|$)/.test(value)) return '/projects'
  return value
}
