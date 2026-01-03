import ResumeBuilder from './components/ResumeBuilder';
import './App.css';

function App() {
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
      </div>

      <div className="body body-resume">
        <ResumeBuilder />
      </div>
    </div>
  );
}

export default App;
