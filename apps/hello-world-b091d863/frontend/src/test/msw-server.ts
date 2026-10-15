import { setupServer } from 'msw/node'
import { http, HttpResponse } from 'msw'

export const handlers = {
  statusSignedIn: http.get('/api/v1/auth/status', () =>
    HttpResponse.json({
      authenticated: true,
      user: { email: 'alice@example.com', name: 'Alice' },
    }),
  ),
  statusSignedOut: http.get('/api/v1/auth/status', () =>
    HttpResponse.json({ authenticated: false, user: null }),
  ),
  hello: http.get('/api/v1/hello', () =>
    HttpResponse.json({ message: 'Hello, world! 👋 Welcome, Alice.' }),
  ),
  helloError: http.get('/api/v1/hello', () =>
    HttpResponse.json({ error: { code: 'oops', message: 'Service unavailable' } }, { status: 500 }),
  ),
  logout: http.post('/api/v1/auth/logout', () => new HttpResponse(null, { status: 303 })),
}

export const server = setupServer(handlers.statusSignedOut, handlers.hello, handlers.logout)
