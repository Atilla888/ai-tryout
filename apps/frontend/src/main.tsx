import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { AuthProvider } from 'react-oidc-context'
import { WebStorageStateStore } from 'oidc-client-ts'
import './index.css'
import App from './App.tsx'

// OIDC Authorization Code Flow + PKCE against the Keycloak realm.
const oidcConfig = {
  authority: import.meta.env.VITE_OIDC_AUTHORITY ?? 'http://localhost:8080/realms/ai-spaces',
  client_id: import.meta.env.VITE_OIDC_CLIENT_ID ?? 'ai-spaces-frontend',
  redirect_uri: window.location.origin,
  post_logout_redirect_uri: window.location.origin,
  scope: 'openid profile email',
  // Persist the session across reloads instead of in-memory only.
  userStore: new WebStorageStateStore({ store: window.localStorage }),
  // Strip ?code=&state= from the URL after Keycloak redirects back.
  onSigninCallback: () =>
    window.history.replaceState({}, document.title, window.location.pathname),
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider {...oidcConfig}>
      <App />
    </AuthProvider>
  </StrictMode>,
)
