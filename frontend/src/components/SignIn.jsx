import { useState } from 'react';

export function SignIn({ onSubmit, error, busy = false }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [localError, setLocalError] = useState(null);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!username.trim() || !password) {
      setLocalError('Enter the operator username and password.');
      return;
    }
    setLocalError(null);
    await onSubmit(username.trim(), password);
  }

  const message = localError ?? error;

  return (
    <div className="sheet-backdrop">
      <section
        className="signin-sheet sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="signin-title"
      >
        <p className="engraved">AUTHENTICATION REQUIRED</p>
        <h1 id="signin-title">Sign in to the console</h1>
        <p>
          The API requires a bearer token. The token is kept for this browser session only.
        </p>
        <form onSubmit={handleSubmit} noValidate>
          <label htmlFor="signin-username">Username</label>
          <input
            id="signin-username"
            autoComplete="username"
            autoFocus
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          />
          <label htmlFor="signin-password">Password</label>
          <input
            id="signin-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {message && <p className="form-error" role="alert">{message}</p>}
          <button type="submit" className="primary-button" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </section>
    </div>
  );
}
