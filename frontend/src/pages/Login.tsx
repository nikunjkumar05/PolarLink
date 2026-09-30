import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { api, ApiError } from '../api/client'
import { useAuth } from '../lib/useAuth'
import type { User } from '../types'

export default function Login() {
  const { user, signIn } = useAuth()
  const navigate = useNavigate()
  const [directory, setDirectory] = useState<User[]>([])
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (user) navigate('/articles', { replace: true })
  }, [user, navigate])

  useEffect(() => {
    api.directory().then(setDirectory).catch(() => setDirectory([]))
  }, [])

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await signIn(email.trim(), password)
      navigate('/articles', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'could not sign in')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="narrow auth-card">
      <h1>Sign in</h1>
      <p className="muted">
        Editing, review and publishing need an account. Reading and searching stay open to everyone.
      </p>

      <form className="auth-form" onSubmit={submit}>
        <label className="field">
          <span>Email</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="editor@ncpor.in"
            autoComplete="username"
            required
          />
        </label>
        <label className="field">
          <span>Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            autoComplete="current-password"
            required
          />
        </label>
        {error && <p className="error-box">{error}</p>}
        <button className="btn primary" type="submit" disabled={busy}>
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
      </form>

      {directory.length > 0 && (
        <div className="account-list">
          <h2>Demo accounts</h2>
          <p className="small muted">One click fills the form — these are seeded by demo.py.</p>
          <ul>
            {directory.map((account) => (
              <li key={account.id}>
                <button
                  type="button"
                  className="account-row"
                  onClick={() => {
                    setEmail(account.email)
                    setPassword(`${account.role.toLowerCase()}123`)
                  }}
                >
                  <strong>{account.name}</strong>
                  <span className="chip">{account.role}</span>
                  <span className="small muted">{account.email}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}