import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect } from 'vitest'
import App from './App'
import { server, handlers } from './test/msw-server'

describe('App', () => {
  it('shows a sign-in prompt when the user is signed out', async () => {
    server.use(handlers.statusSignedOut)
    render(<App />)
    expect(await screen.findByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('shows the greeting when the user is signed in', async () => {
    server.use(handlers.statusSignedIn, handlers.hello)
    render(<App />)
    expect(await screen.findByRole('heading', { name: /hello, world/i })).toBeInTheDocument()
    expect(screen.getByText(/alice@example.com/i)).toBeInTheDocument()
  })

  it('shows an error when the hello endpoint fails', async () => {
    server.use(handlers.statusSignedIn, handlers.helloError)
    render(<App />)
    expect(await screen.findByRole('alert')).toHaveTextContent(/service unavailable/i)
  })

  it('signs out when the sign-out button is pressed', async () => {
    server.use(handlers.statusSignedIn, handlers.hello, handlers.logout)
    render(<App />)
    const btn = await screen.findByRole('button', { name: /sign out/i })
    await userEvent.click(btn)
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument(),
    )
  })
})
