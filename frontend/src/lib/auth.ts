// In local dev (VITE_AUTH_MODE=mock) we skip Cognito entirely and store a
// fake token so the API interceptor has something to send.
// In staging/prod set VITE_AUTH_MODE=cognito and fill the other vars.

export const AUTH_MODE = import.meta.env.VITE_AUTH_MODE ?? 'mock'

export const amplifyConfig = {
  Auth: {
    Cognito: {
      userPoolId: import.meta.env.VITE_USER_POOL_ID ?? '',
      userPoolClientId: import.meta.env.VITE_USER_POOL_CLIENT_ID ?? '',
      loginWith: { email: true },
    },
  },
}

export const MOCK_USER = {
  adjuster_id: 'ADJ-LOCAL-001',
  name: 'Local Adjuster',
  email: 'adjuster@autosure.local',
}

export function seedMockToken() {
  if (!localStorage.getItem('id_token')) {
    localStorage.setItem('id_token', 'mock-token-dev')
    localStorage.setItem('adjuster_id', MOCK_USER.adjuster_id)
    localStorage.setItem('adjuster_name', MOCK_USER.name)
  }
}

export function getAdjusterId(): string {
  return localStorage.getItem('adjuster_id') ?? MOCK_USER.adjuster_id
}

export function clearAuth() {
  localStorage.removeItem('id_token')
  localStorage.removeItem('adjuster_id')
  localStorage.removeItem('adjuster_name')
}
