export default function AuthPanel({
  accessCode,
  authBusy,
  busy,
  isAuthenticated,
  liveBusy,
  onLogin,
  onLogout,
  requiresAccessCode,
  sessionUser,
  setAccessCode,
  setPassword,
  setUsername,
  skipUploadValidations,
  uploadCount,
  username,
  password,
}) {
  return (
    <div className="authPanel">
      <div>
        <strong>{isAuthenticated ? `Signed in as ${sessionUser || username}` : 'Authentication required'}</strong>
        <div className="small">API access is protected with a secure session cookie. Configure backend credentials with environment variables.</div>
        {isAuthenticated ? <div className="small">Uploads from this IP: {uploadCount}</div> : null}
        {isAuthenticated && skipUploadValidations ? <div className="small">Pre-upload validations are skipped for this IP address.</div> : null}
      </div>
      {isAuthenticated ? (
        <button type="button" className="secondaryButton" onClick={onLogout} disabled={busy || liveBusy}>Log out</button>
      ) : (
        <form className="authForm" onSubmit={onLogin}>
          <input type="text" placeholder="Username" value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" required />
          <input type="password" placeholder="Password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required />
          {requiresAccessCode ? <input type="password" placeholder="Access code" value={accessCode} onChange={(event) => setAccessCode(event.target.value)} autoComplete="one-time-code" required /> : null}
          <button type="submit" disabled={authBusy || !username || !password || (requiresAccessCode && !accessCode)}>{authBusy ? 'Signing in…' : 'Sign in'}</button>
        </form>
      )}
    </div>
  )
}
