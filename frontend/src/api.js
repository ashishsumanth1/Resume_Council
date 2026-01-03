/**
 * API client for the LLM Council backend.
 */

const RAW_API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8001';
const API_BASE = RAW_API_BASE.replace(/\/$/, '');

export const api = {
  /**
   * Run resume tailoring council flow.
   */
  async runResume({ jobDescription, masterProfile, companyDetails, profileId, usePeerRanking }) {
    const response = await fetch(`${API_BASE}/api/resume/run`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        job_description: jobDescription,
        master_profile: masterProfile,
        profile_id: profileId,
        company_details: companyDetails,
        use_peer_ranking: typeof usePeerRanking === 'boolean' ? usePeerRanking : null,
      }),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || 'Failed to run resume flow');
    }

    return response.json();
  },

  async listResumeRuns() {
    const response = await fetch(`${API_BASE}/api/resumes`);
    if (!response.ok) {
      throw new Error('Failed to list resume runs');
    }
    return response.json();
  },

  async getResumeRun(resumeId) {
    const response = await fetch(`${API_BASE}/api/resumes/${resumeId}`);
    if (!response.ok) {
      throw new Error('Failed to get resume run');
    }
    return response.json();
  },

  async listProfiles() {
    const response = await fetch(`${API_BASE}/api/profiles`);
    if (!response.ok) {
      throw new Error('Failed to list profiles');
    }
    return response.json();
  },

  async createProfile({ name, rawText }) {
    const response = await fetch(`${API_BASE}/api/profiles`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ name, raw_text: rawText }),
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || 'Failed to create profile');
    }
    return response.json();
  },

  async getProfile(profileId) {
    const response = await fetch(`${API_BASE}/api/profiles/${profileId}`);
    if (!response.ok) {
      throw new Error('Failed to get profile');
    }
    return response.json();
  },
};
