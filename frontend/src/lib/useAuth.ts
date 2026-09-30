import { useCallback, useEffect, useState } from 'react'

import { api, getToken, setToken } from '../api/client'
import type { User } from '../types'

/** Holds the signed-in user for the editorial screens (FR-01). */
export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [checked, setChecked] = useState(!getToken())

  useEffect(() => {
    if (!getToken()) return
    let cancelled = false
    api
      .me()
      .then((value) => {
        if (!cancelled) setUser(value)
      })
      .catch(() => setToken(null))
      .finally(() => {
        if (!cancelled) setChecked(true)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const signIn = useCallback(async (email: string, password: string) => {
    const session = await api.login(email, password)
    setToken(session.access_token)
    setUser(session.user)
    return session.user
  }, [])

  const signOut = useCallback(() => {
    setToken(null)
    setUser(null)
  }, [])

  const can = useCallback(
    (...roles: string[]) => !!user && (user.role === 'ADMIN' || roles.includes(user.role)),
    [user],
  )

  return { user, ready: checked, signIn, signOut, can, isReviewer: can('REVIEWER'), isEditor: can('EDITOR') }
}