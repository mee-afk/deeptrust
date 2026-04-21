/**
 * DeepTrust Login & User Authentication Component
 * ===============================================
 * This component provides the entrance for user registration and authentication.
 * It also serves as an alternative/simplified dashboard for media analysis 
 * for non-authenticated sessions or quick testing.
 * 
 * Features:
 * - Login/Register form transitions.
 * - Local file ingestion and preview.
 * - direct API communication for media analysis (bypassing gateway for direct service testing).
 * - JSON report export capabilities.
 */

import {
  AlertCircle,
  Upload
} from 'lucide-react';
import { useRef, useState } from 'react';

const Login = () => {
  // ── Core Navigation State ──────────────────────────────────────────────────
  const [currentPage, setCurrentPage] = useState('login'); // 'login' | 'register' | 'app'
  
  // ── Media Ingestion State ──────────────────────────────────────────────────
  const [file, setFile] = useState(null);            // Raw media file
  const [preview, setPreview] = useState(null);      // Local preview URL
  const [analyzing, setAnalyzing] = useState(false); // Inference loading state
  const [results, setResults] = useState(null);      // Parsed API response
  const [error, setError] = useState(null);          // Error boundary state
  const [activeTab, setActiveTab] = useState('overview'); // UI Result Tab
  const [analysisStage, setAnalysisStage] = useState(''); // Textual loading feedback
  
  // ── Authentication & User State ────────────────────────────────────────────
  const [showPassword, setShowPassword] = useState(false);
  const [currentUser, setCurrentUser] = useState(null); // Active session profile
  const [loginForm, setLoginForm] = useState({ email: '', password: '' });
  const [registerForm, setRegisterForm] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [formError, setFormError] = useState(''); // validation error state
  
  const fileInputRef = useRef(null);

  /**
   * Processes the user login request.
   * Note: This implementation simulates a successful login.
   * @param {Event} e 
   */
  const handleLogin = (e) => {
    e.preventDefault();
    setFormError('');

    if (!loginForm.email || !loginForm.password) {
      setFormError('Identity credentials required to proceed.');
      return;
    }

    // Simulate network delay and successful authentication
    setTimeout(() => {
      setCurrentUser({
        email: loginForm.email,
        username: loginForm.email.split('@')[0],
      });
      setCurrentPage('app');
    }, 800);
  };

  /**
   * Processes the account creation request.
   * Note: This implementation simulates a successful registration.
   * @param {Event} e 
   */
  const handleRegister = (e) => {
    e.preventDefault();
    setFormError('');

    // Primary validation checks
    if (
      !registerForm.username ||
      !registerForm.email ||
      !registerForm.password ||
      !registerForm.confirmPassword
    ) {
      setFormError('All fields are mandatory for security profile creation.');
      return;
    }

    if (registerForm.password !== registerForm.confirmPassword) {
      setFormError('Verification password does not match original.');
      return;
    }

    if (registerForm.password.length < 8) {
      setFormError('Password must exceed 8 characters for minimum strength.');
      return;
    }

    // Simulate network latency and session creation
    setTimeout(() => {
      setCurrentUser({
        email: registerForm.email,
        username: registerForm.username,
      });
      setCurrentPage('app');
    }, 800);
  };

  /**
   * Terminates the active session and resets application data.
   */
  const handleLogout = () => {
    setCurrentUser(null);
    setCurrentPage('login');
    setFile(null);
    setResults(null);
  };

  /**
   * Handles media selection and establishes local viewport preview.
   * @param {Event} e 
   */
  const handleFileSelect = (e) => {
    const selected = e.target.files?.[0];
    if (!selected) return;

    if (
      selected.type.startsWith('image/') ||
      selected.type.startsWith('video/')
    ) {
      setFile(selected);
      setResults(null);
      setError(null);

      const reader = new FileReader();
      reader.onloadend = () => setPreview(reader.result);
      reader.readAsDataURL(selected);
    } else {
      setError('Unsupported file signature. Please provides images or videos.');
    }
  };

  /**
   * Executes a direct analysis request to the backend.
   * This is used for standalone testing and authenticated quick-scans.
   */
  const analyzeMedia = async () => {
    if (!file) return;

    setAnalyzing(true);
    setError(null);
    setAnalysisStage('Relaying media to inference cluster...');

    try {
      const formData = new FormData();
      formData.append('file', file);

      setAnalysisStage('Executing neural ensemble...');

      // Direct communication with the analysis service for development contexts
      const response = await fetch('http://localhost:8000/api/analyze', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Inference cluster rejected the request.');
      }

      const data = await response.json();

      // Mapping API response to internal dashboard state
      setResults({
        isDeepfake: data.is_deepfake,
        confidence: data.ensemble_score,
        models: data.model_scores,
        artifacts: data.artifacts || [],
        gradcam: data.gradcam_image,
        metadata: data.metadata,
        processingTime: data.processing_time,
      });
    } catch (err) {
      setError(
        err.message ||
          'Inference service unreachable. Confirm services are operational on port 8000.'
      );
    } finally {
      setAnalyzing(false);
      setAnalysisStage('');
    }
  };

  /**
   * Exports the qualitative and quantitative analysis results as a JSON blob.
   */
  const downloadReport = () => {
    if (!results) return;

    const blob = new Blob([JSON.stringify(results, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `deeptrust-forensic-report-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  /**
   * Semantic color selection for confidence highlighting.
   * @param {number} v - Confidence score [0-1].
   */
  const confidenceColor = (v) =>
    v > 0.8 ? 'text-red-500' : v > 0.6 ? 'text-yellow-400' : 'text-green-400';

  /* ── VIEW: Identity Management (Login) ─────────────────────────────────── */
  if (currentPage === 'login') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900 text-white">
        <form
          onSubmit={handleLogin}
          className="bg-white/10 backdrop-blur-md p-8 rounded-xl w-full max-w-md border border-white/10"
        >
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold tracking-tighter">DeepTrust</h1>
            <p className="text-xs text-blue-400 uppercase tracking-widest mt-1">Unified Security Interface</p>
          </div>

          {formError && (
            <div className="mb-4 text-red-400 flex items-center gap-2 text-sm bg-red-400/10 p-3 rounded-lg">
              <AlertCircle className="w-4 h-4" /> {formError}
            </div>
          )}

          <div className="space-y-4">
            <input
              type="email"
              placeholder="Corporate Email"
              className="w-full p-3 rounded bg-black/40 border border-white/5 focus:border-blue-500/50 outline-none transition-all"
              value={loginForm.email}
              onChange={(e) =>
                setLoginForm({ ...loginForm, email: e.target.value })
              }
            />

            <input
              type="password"
              placeholder="Secure Password"
              className="w-full p-3 rounded bg-black/40 border border-white/5 focus:border-blue-500/50 outline-none transition-all"
              value={loginForm.password}
              onChange={(e) =>
                setLoginForm({ ...loginForm, password: e.target.value })
              }
            />

            <button className="w-full bg-blue-600 hover:bg-blue-700 py-3 rounded font-bold uppercase tracking-widest transition-all">
              Establish Session
            </button>
          </div>

          <p className="mt-6 text-center text-xs text-gray-500">
            Internal access only. Require account?{' '}
            <button
              type="button"
              onClick={() => setCurrentPage('register')}
              className="text-blue-400 hover:underline"
            >
              Request Access
            </button>
          </p>
        </form>
      </div>
    );
  }

  /* ── VIEW: Identity Management (Register) ──────────────────────────────── */
  if (currentPage === 'register') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900 text-white">
        <form
          onSubmit={handleRegister}
          className="bg-white/10 backdrop-blur-md p-8 rounded-xl w-full max-w-md border border-white/10"
        >
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold tracking-tighter">Security Profile</h1>
            <p className="text-xs text-blue-400 uppercase tracking-widest mt-1">Credential setup</p>
          </div>

          {formError && (
            <div className="mb-4 text-red-400 flex items-center gap-2 text-sm bg-red-400/10 p-3 rounded-lg">
              <AlertCircle className="w-4 h-4" /> {formError}
            </div>
          )}

          <div className="space-y-3">
             <input
              placeholder="Profile Username"
              className="w-full p-3 rounded bg-black/40 border border-white/5 focus:border-blue-500/50 outline-none transition-all"
              value={registerForm.username}
              onChange={(e) =>
                setRegisterForm({ ...registerForm, username: e.target.value })
              }
            />

            <input
              placeholder="Audit Email"
              className="w-full p-3 rounded bg-black/40 border border-white/5 focus:border-blue-500/50 outline-none transition-all"
              value={registerForm.email}
              onChange={(e) =>
                setRegisterForm({ ...registerForm, email: e.target.value })
              }
            />

            <input
              type="password"
              placeholder="Secure Password"
              className="w-full p-3 rounded bg-black/40 border border-white/5 focus:border-blue-500/50 outline-none transition-all"
              value={registerForm.password}
              onChange={(e) =>
                setRegisterForm({ ...registerForm, password: e.target.value })
              }
            />

            <input
              type="password"
              placeholder="Confirm Password"
              className="w-full p-3 rounded bg-black/40 border border-white/5 focus:border-blue-500/50 outline-none transition-all"
              value={registerForm.confirmPassword}
              onChange={(e) =>
                setRegisterForm({
                  ...registerForm,
                  confirmPassword: e.target.value,
                })
              }
            />

            <button className="w-full bg-blue-600 hover:bg-blue-700 py-3 rounded font-bold uppercase tracking-widest transition-all mt-4">
              Finalize Registration
            </button>
          </div>

          <p className="mt-6 text-center text-xs text-gray-500">
            Already have security credentials?{' '}
            <button
              type="button"
              onClick={() => setCurrentPage('login')}
              className="text-blue-400 hover:underline"
            >
              Sign In
            </button>
          </p>
        </form>
      </div>
    );
  }

  /* ── VIEW: Primary Workspace Dashboard ─────────────────────────────────── */
  return (
    <div className="min-h-screen bg-slate-900 text-white p-8">
      <div className="flex justify-between items-center mb-8 pb-4 border-b border-white/5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Security Command Center</h1>
          <p className="text-xs text-gray-500 font-medium">Session ID: {currentUser.username.toUpperCase()}-{Date.now().toString().slice(-6)}</p>
        </div>
        <button
          onClick={handleLogout}
          className="bg-red-500/10 hover:bg-red-500/20 text-red-400 px-4 py-2 rounded-lg text-xs font-bold transition-all border border-red-500/20"
        >
          Terminate Session
        </button>
      </div>

      {/* Media Ingestion Viewport */}
      {!file && (
        <div
          onClick={() => fileInputRef.current.click()}
          className="border-2 border-dashed border-white/10 p-24 rounded-2xl text-center cursor-pointer hover:bg-white/5 hover:border-blue-500/50 transition-all group"
        >
          <Upload className="mx-auto mb-4 w-12 h-12 text-blue-500 group-hover:scale-110 transition-transform" />
          <p className="text-lg font-bold">Initiate Media Request</p>
          <p className="text-sm text-gray-500">Select images or videos for neural scanning</p>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={handleFileSelect}
          />
        </div>
      )}

      {/* Active Workspace / Result Presentation */}
      {file && (
        <div className="grid md:grid-cols-2 gap-8">
          <div className="space-y-4">
            <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest">Workspace Viewport</h3>
            {preview && (
              <div className="aspect-video bg-black rounded-xl overflow-hidden border border-white/5 relative">
                 {file.type.startsWith('image/') ? (
                    <img src={preview} alt="preview" className="w-full h-full object-contain" />
                 ) : (
                    <video src={preview} controls className="w-full h-full object-contain" />
                 )}
              </div>
            )}
            <button
              onClick={analyzeMedia}
              disabled={analyzing}
              className="w-full bg-blue-600 hover:bg-blue-700 py-4 rounded-xl font-bold uppercase tracking-widest transition-all shadow-lg active:scale-95 disabled:opacity-50"
            >
              {analyzing ? 'Inference Synchronizing...' : 'Begin Forensic Scan'}
            </button>
          </div>

          <div className="bg-white/5 p-6 rounded-2xl border border-white/5 self-start">
            {results ? (
              <div className="space-y-6">
                <div>
                   <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-4">Inference Summary</h3>
                   <div className="flex items-center justify-between p-4 bg-black/40 rounded-xl border border-white/5">
                      <span className="text-sm font-bold">Detection Verdict:</span>
                      <span className={`text-lg font-black uppercase tracking-tighter ${confidenceColor(results.confidence)}`}>
                        {results.isDeepfake ? 'Signal Manipulated' : 'Source Authentic'}
                      </span>
                   </div>
                </div>

                <div className="space-y-2">
                   <div className="flex justify-between items-center text-xs text-gray-400">
                      <span>Statistical Confidence</span>
                      <span>{(results.confidence * 100).toFixed(2)}%</span>
                   </div>
                   <div className="h-1.5 bg-black/40 rounded-full overflow-hidden">
                      <div className={`h-full bg-blue-500 transition-all duration-1000`} style={{ width: `${results.confidence * 100}%` }} />
                   </div>
                </div>

                <div className="pt-4 border-t border-white/5">
                  <button
                    onClick={downloadReport}
                    className="w-full bg-green-600/10 hover:bg-green-600/20 text-green-400 border border-green-600/20 px-4 py-3 rounded-xl text-xs font-bold uppercase tracking-widest transition-all"
                  >
                    Download Forensic JSON
                  </button>
                </div>
              </div>
            ) : (
              <div className="py-24 text-center">
                 <Brain className="mx-auto w-12 h-12 text-white/5 mb-4"/>
                 <p className="text-xs text-gray-600 uppercase font-bold tracking-widest">
                   Waiting for signal analysis stimulus...
                 </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default Login;