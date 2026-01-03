import { useEffect, useMemo, useState } from 'react';
import ResumeBuilder from './components/ResumeBuilder';
import { api, auth } from './api';
import './App.css';

function App() {
  const [dark, setDark] = useState(() => {
    if (typeof window === 'undefined') return false;
    const saved = localStorage.getItem('theme');
    if (saved) return saved === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    localStorage.setItem('theme', dark ? 'dark' : 'light');
  }, [dark]);

  const [isAuthed, setIsAuthed] = useState(() => auth.has());
  const [authStatus, setAuthStatus] = useState(() => (auth.has() ? 'checking' : 'idle'));
  const [authError, setAuthError] = useState('');
  const [authLoading, setAuthLoading] = useState(false);
  const [credentials, setCredentials] = useState({ email: '', password: '', totp: '' });

  useEffect(() => {
    if (!auth.has()) return;
    setAuthStatus('checking');
    api
      .listProfiles()
      .then(() => {
        setIsAuthed(true);
        setAuthStatus('authed');
      })
      .catch(() => {
        auth.clear();
        setIsAuthed(false);
        setAuthStatus('idle');
      });
  }, []);

  const handleLogin = async (event) => {
    event.preventDefault();
    setAuthError('');
    setAuthLoading(true);
    try {
      const data = await api.login(credentials);
      auth.set(data.token);
      setIsAuthed(true);
      setAuthStatus('authed');
    } catch (err) {
      auth.clear();
      setIsAuthed(false);
      setAuthStatus('idle');
      setAuthError('Invalid email or password.');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    auth.clear();
    setCredentials({ email: '', password: '' });
    setIsAuthed(false);
    setAuthStatus('idle');
  };

  const heroDescription = useMemo(() => {
    return 'Private access. Sign in to generate role-ready resumes with the council.';
  }, []);

  return (
    <div className="app">
      <div className="topbar">
        <div className="brand">
          <div className="brand-mark">RC</div>
          <div className="brand-text">
            <div className="brand-title">Resume Council</div>
            <div className="brand-subtitle">LLM powered resume tailoring</div>
          </div>
        </div>
        <div className="topbar-actions">
          {isAuthed && authStatus === 'authed' && (
            <button className="ghost-button" type="button" onClick={handleLogout}>
              Sign out
            </button>
          )}
          <button
            className="theme-toggle"
            type="button"
            onClick={() => setDark((prev) => !prev)}
          >
            {dark ? 'Light mode' : 'Dark mode'}
          </button>
        </div>
      </div>

      {!isAuthed || authStatus !== 'authed' ? (
        <div className="auth-shell">
          <div className="auth-card card">
            <span className="badge badge-accent">Private Access</span>
            <h1>Resume Council</h1>
            <p>{heroDescription}</p>
            <form className="auth-form" onSubmit={handleLogin}>
              <label className="auth-field">
                Email
                <input
                  type="email"
                  required
                  value={credentials.email}
                  onChange={(event) =>
                    setCredentials((prev) => ({ ...prev, email: event.target.value }))
                  }
                  placeholder="you@domain.com"
                />
              </label>
              <label className="auth-field">
                Password
                <input
                  type="password"
                  required
                  value={credentials.password}
                  onChange={(event) =>
                    setCredentials((prev) => ({ ...prev, password: event.target.value }))
                  }
                  placeholder="••••••••"
                />
              </label>
              <label className="auth-field">
                Authenticator code
                <input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  required
                  value={credentials.totp}
                  onChange={(event) =>
                    setCredentials((prev) => ({ ...prev, totp: event.target.value }))
                  }
                  placeholder="123456"
                />
              </label>
              {authError && <div className="auth-error">{authError}</div>}
              <button className="run-button" type="submit" disabled={authLoading}>
                {authLoading ? 'Checking…' : 'Continue'}
              </button>
            </form>
          </div>
        </div>
      ) : (
        <div className="body body-resume">
          <ResumeBuilder />
        </div>
      )}
    </div>
  );
}

export default App;
