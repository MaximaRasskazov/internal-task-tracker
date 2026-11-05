export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details: { field: string; message: string }[] = [],
    public retryAfter = 0,
  ) {
    super(message)
  }
}
let csrf: string | null = null
let onUnauthorized = () => {}
export function configureSession(token: string | null) {
  csrf = token
}
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler
}
type Options = {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
  body?: unknown
  signal?: AbortSignal
  public?: boolean
}
export async function request<T>(path: string, options: Options = {}): Promise<T> {
  const method = options.method || 'GET'
  const headers = new Headers({ Accept: 'application/json' })
  if (options.body !== undefined) headers.set('Content-Type', 'application/json')
  if (method !== 'GET' && !options.public && csrf) headers.set('X-CSRF-Token', csrf)
  let response: Response
  try {
    response = await fetch('/api/v1' + path, {
      method,
      headers,
      credentials: 'include',
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal
        ? AbortSignal.any([options.signal, AbortSignal.timeout(20000)])
        : AbortSignal.timeout(20000),
    })
  } catch (error) {
    if (options.signal?.aborted) throw error
    throw new ApiError(
      0,
      'NETWORK_ERROR',
      method === 'GET'
        ? 'Не удалось связаться с сервером. Проверьте подключение и повторите загрузку.'
        : 'Ответ сервера не получен. Изменение могло сохраниться. Проверьте данные перед повторной отправкой.',
    )
  }
  if (!response.ok) {
    const data = await response.json().catch(() => null)
    if (response.status === 401 && !options.public) onUnauthorized()
    const error = data?.error
    const rawRetry = response.headers.get('Retry-After')
    const retryAfter = rawRetry
      ? Number(rawRetry) || Math.max(0, Math.ceil((Date.parse(rawRetry) - Date.now()) / 1000))
      : 0
    throw new ApiError(
      response.status,
      error?.code || 'HTTP_ERROR',
      error?.message || 'Сервис временно недоступен. Попробуйте позже.',
      error?.details || [],
      retryAfter,
    )
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}
export function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : 'Не удалось выполнить действие.'
}
export function fieldError(error: unknown, field: string) {
  return error instanceof ApiError
    ? error.details.find((d) => d.field === field || d.field.endsWith('.' + field))?.message
    : undefined
}
