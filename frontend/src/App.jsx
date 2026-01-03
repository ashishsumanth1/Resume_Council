import ResumeBuilder from './components/ResumeBuilder';
import './App.css';

function App() {
  return (
    <div className="app">
      <div className="topbar">
        <div className="brand">Resume Council</div>
      </div>

      <div className="body body-resume">
        <ResumeBuilder />
      </div>
    </div>
  );
}

export default App;
