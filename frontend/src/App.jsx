import { useEffect, useState } from 'react';
import ResumeBuilder from './components/ResumeBuilder';
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
          <button
            className="theme-toggle"
            type="button"
            onClick={() => setDark((prev) => !prev)}
          >
            {dark ? 'Light mode' : 'Dark mode'}
          </button>
        </div>
      </div>

      <div className="body body-resume">
        <ResumeBuilder />
      </div>
    </div>
  );
}

export default App;
