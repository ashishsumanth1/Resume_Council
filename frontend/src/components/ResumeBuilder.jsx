import { useEffect, useState } from 'react';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Stage3 from './Stage3';
import { api } from '../api';
import './ResumeBuilder.css';

export default function ResumeBuilder() {
  const [history, setHistory] = useState([]);
  const [selectedResumeId, setSelectedResumeId] = useState(null);
  const [profiles, setProfiles] = useState([]);
  const [selectedProfileId, setSelectedProfileId] = useState('');
  const [usePeerRanking, setUsePeerRanking] = useState(true);
  const [jobDescription, setJobDescription] = useState('');
  const [masterProfile, setMasterProfile] = useState('');
  const [companyDetails, setCompanyDetails] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const loadHistory = async () => {
    try {
      const items = await api.listResumeRuns();
      setHistory(items);
    } catch (e) {
      // non-fatal
      console.error(e);
    }
  };

  useEffect(() => {
    loadHistory();
    (async () => {
      try {
        const items = await api.listProfiles();
        setProfiles(items);
      } catch (e) {
        console.error(e);
      }
    })();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setResult(null);
    setSelectedResumeId(null);
    if (!jobDescription.trim() || (!masterProfile.trim() && !selectedProfileId)) {
      setError('Job description and master profile are required.');
      return;
    }
    setIsLoading(true);
    try {
      const data = await api.runResume({
        jobDescription,
        masterProfile: selectedProfileId ? '' : masterProfile,
        companyDetails,
        profileId: selectedProfileId || null,
        usePeerRanking,
      });
      // Backend now returns a persisted record: {id, created_at, title, inputs, result}
      setSelectedResumeId(data.id);
      setResult(data.result);
      await loadHistory();
    } catch (err) {
      setError(err.message || 'Failed to generate resume.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveProfile = async () => {
    setError('');
    if (!masterProfile.trim()) {
      setError('Paste your master profile first, then save it.');
      return;
    }
    setIsLoading(true);
    try {
      await api.createProfile({ name: 'Master Profile', rawText: masterProfile });
      const items = await api.listProfiles();
      setProfiles(items);
    } catch (err) {
      setError(err.message || 'Failed to save profile.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectProfile = async (profileId) => {
    setSelectedProfileId(profileId);
    if (!profileId) return;
    setIsLoading(true);
    setError('');
    try {
      const p = await api.getProfile(profileId);
      setMasterProfile(p.raw_text || '');
    } catch (err) {
      setError(err.message || 'Failed to load profile.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectHistory = async (resumeId) => {
    setError('');
    setIsLoading(true);
    try {
      const record = await api.getResumeRun(resumeId);
      setSelectedResumeId(record.id);
      setJobDescription(record.inputs?.job_description || '');
      setMasterProfile(record.inputs?.master_profile || '');
      setCompanyDetails(record.inputs?.company_details || '');
      setUsePeerRanking(
        typeof record.inputs?.use_peer_ranking === 'boolean' ? record.inputs.use_peer_ranking : true
      );
      setResult(record.result);
    } catch (err) {
      setError(err.message || 'Failed to load saved resume run.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownload = () => {
    if (!result?.docx?.base64) return;
    const byteCharacters = atob(result.docx.base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i += 1) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = result.docx.filename || 'tailored_resume.docx';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="resume-builder">
      <section className="resume-hero card fade-in">
        <h1>Role-ready resumes, without the busywork.</h1>
        <p>
          Drop in a job description and your master profile. The council drafts,
          ranks, and refines a tailored resume you can export as DOCX.
        </p>
      </section>
      <div className="resume-layout">
        <div className="resume-history card">
          <div className="resume-history-header">
            <span>History</span>
            <span className="badge">Saved runs</span>
          </div>
          {history.length === 0 ? (
            <div className="resume-history-empty">No resume runs yet</div>
          ) : (
            history.map((item) => (
              <button
                key={item.id}
                className={`resume-history-item ${item.id === selectedResumeId ? 'active' : ''}`}
                onClick={() => handleSelectHistory(item.id)}
                type="button"
              >
                <div className="resume-history-title">{item.title || 'Resume Run'}</div>
                <div className="resume-history-meta">{new Date(item.created_at).toLocaleString()}</div>
              </button>
            ))
          )}
        </div>

        <div className="resume-main">
          <div className="resume-form-card card">
            <div className="form-header">
              <div>
                <h2>Start a run</h2>
                <p>
                  Paste the role description and your master profile. You can
                  save profiles and reuse them across runs.
                </p>
              </div>
            </div>

            {error && <div className="error-banner">{error}</div>}

            <form className="resume-form" onSubmit={handleSubmit}>
              <label>
                Peer Ranking (expensive, higher confidence)
                <div className="toggle-row">
                  <input
                    type="checkbox"
                    checked={usePeerRanking}
                    onChange={(e) => setUsePeerRanking(e.target.checked)}
                    disabled={isLoading}
                  />
                  <span>{usePeerRanking ? 'On' : 'Off'}</span>
                </div>
              </label>

              <label>
                Job Description (paste text)
                <textarea
                  value={jobDescription}
                  onChange={(e) => setJobDescription(e.target.value)}
                  placeholder="Paste the JD here"
                  rows={8}
                  required
                />
              </label>

              <label>
                Master Profile (truth source)
                <div className="profile-row">
                  <select
                    className="profile-select"
                    value={selectedProfileId}
                    onChange={(e) => handleSelectProfile(e.target.value)}
                    disabled={isLoading}
                  >
                    <option value="">(not saved)</option>
                    {profiles.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name || 'Master Profile'}
                      </option>
                    ))}
                  </select>
                  <button
                    className="save-profile-button"
                    type="button"
                    onClick={handleSaveProfile}
                    disabled={isLoading}
                  >
                    Save
                  </button>
                </div>
                <textarea
                  value={masterProfile}
                  onChange={(e) => setMasterProfile(e.target.value)}
                  placeholder="Paste your master resume/profile"
                  rows={8}
                />
              </label>

              <label>
                Company Details (optional)
                <textarea
                  value={companyDetails}
                  onChange={(e) => setCompanyDetails(e.target.value)}
                  placeholder="Any notes on company culture, values, products"
                  rows={4}
                />
              </label>

              <button type="submit" className="run-button" disabled={isLoading}>
                {isLoading ? 'Working…' : 'Run Council'}
              </button>
            </form>
          </div>

      {isLoading && (
        <div className="loading-banner">Consulting the council…</div>
      )}

      {result && (
        <div className="results">
          <div className="result-actions">
            {result.docx?.base64 && (
              <button className="download-button" onClick={handleDownload}>
                Download DOCX
              </button>
            )}
          </div>
          <Stage1 responses={result.stage1} />
          <Stage2
            rankings={result.stage2}
            labelToModel={result.metadata?.label_to_model}
            aggregateRankings={result.metadata?.aggregate_rankings}
            peerRankingUsed={
              typeof result.metadata?.peer_ranking_used === 'boolean'
                ? result.metadata.peer_ranking_used
                : usePeerRanking
            }
          />
          <Stage3 finalResponse={result.stage3} />
        </div>
      )}
        </div>
      </div>
    </div>
  );
}
