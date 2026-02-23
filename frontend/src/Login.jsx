import {
  AlertCircle,
  Upload
} from 'lucide-react';
import { useRef, useState } from 'react';

const Login = () => {
  const [currentPage, setCurrentPage] = useState('login'); // login | register | app
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [analysisStage, setAnalysisStage] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const fileInputRef = useRef(null);

  /* ---------------- AUTH FORMS ---------------- */
  const [loginForm, setLoginForm] = useState({ email: '', password: '' });
  const [registerForm, setRegisterForm] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [formError, setFormError] = useState('');

  const handleLogin = (e) => {
    e.preventDefault();
    setFormError('');

    if (!loginForm.email || !loginForm.password) {
      setFormError('Please fill in all fields');
      return;
    }

    setTimeout(() => {
      setCurrentUser({
        email: loginForm.email,
        username: loginForm.email.split('@')[0],
      });
      setCurrentPage('app');
    }, 800);
  };

  const handleRegister = (e) => {
    e.preventDefault();
    setFormError('');

    if (
      !registerForm.username ||
      !registerForm.email ||
      !registerForm.password ||
      !registerForm.confirmPassword
    ) {
      setFormError('Please fill in all fields');
      return;
    }

    if (registerForm.password !== registerForm.confirmPassword) {
      setFormError('Passwords do not match');
      return;
    }

    if (registerForm.password.length < 8) {
      setFormError('Password must be at least 8 characters');
      return;
    }

    setTimeout(() => {
      setCurrentUser({
        email: registerForm.email,
        username: registerForm.username,
      });
      setCurrentPage('app');
    }, 800);
  };

  const handleLogout = () => {
    setCurrentUser(null);
    setCurrentPage('login');
    setFile(null);
    setResults(null);
  };

  /* ---------------- FILE HANDLING ---------------- */
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
      setError('Please upload an image or video file');
    }
  };

  /* ---------------- ANALYSIS ---------------- */
  const analyzeMedia = async () => {
    if (!file) return;

    setAnalyzing(true);
    setError(null);
    setAnalysisStage('Uploading media...');

    try {
      const formData = new FormData();
      formData.append('file', file);

      setAnalysisStage('Running AI models...');

      const response = await fetch('http://localhost:8000/api/analyze', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Analysis failed');
      }

      const data = await response.json();

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
          'Backend not reachable. Is FastAPI running on port 8000?'
      );
    } finally {
      setAnalyzing(false);
      setAnalysisStage('');
    }
  };

  const downloadReport = () => {
    if (!results) return;

    const blob = new Blob([JSON.stringify(results, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `deeptrust-report.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const confidenceColor = (v) =>
    v > 0.8 ? 'text-red-500' : v > 0.6 ? 'text-yellow-400' : 'text-green-400';

  /* ================= LOGIN PAGE ================= */
  if (currentPage === 'login') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900 text-white">
        <form
          onSubmit={handleLogin}
          className="bg-white/10 p-8 rounded-xl w-full max-w-md"
        >
          <h1 className="text-3xl font-bold mb-6 text-center">DeepTrust</h1>

          {formError && (
            <div className="mb-4 text-red-400 flex gap-2">
              <AlertCircle /> {formError}
            </div>
          )}

          <input
            type="email"
            placeholder="Email"
            className="w-full mb-3 p-3 rounded bg-black/30"
            value={loginForm.email}
            onChange={(e) =>
              setLoginForm({ ...loginForm, email: e.target.value })
            }
          />

          <input
            type="password"
            placeholder="Password"
            className="w-full mb-4 p-3 rounded bg-black/30"
            value={loginForm.password}
            onChange={(e) =>
              setLoginForm({ ...loginForm, password: e.target.value })
            }
          />

          <button className="w-full bg-blue-600 py-3 rounded font-semibold">
            Sign In
          </button>

          <p className="mt-4 text-center text-sm">
            No account?{' '}
            <button
              type="button"
              onClick={() => setCurrentPage('register')}
              className="text-blue-400"
            >
              Register
            </button>
          </p>
        </form>
      </div>
    );
  }

  /* ================= REGISTER PAGE ================= */
  if (currentPage === 'register') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900 text-white">
        <form
          onSubmit={handleRegister}
          className="bg-white/10 p-8 rounded-xl w-full max-w-md"
        >
          <h1 className="text-3xl font-bold mb-6 text-center">Create Account</h1>

          {formError && (
            <div className="mb-4 text-red-400 flex gap-2">
              <AlertCircle /> {formError}
            </div>
          )}

          <input
            placeholder="Username"
            className="w-full mb-3 p-3 rounded bg-black/30"
            value={registerForm.username}
            onChange={(e) =>
              setRegisterForm({ ...registerForm, username: e.target.value })
            }
          />

          <input
            placeholder="Email"
            className="w-full mb-3 p-3 rounded bg-black/30"
            value={registerForm.email}
            onChange={(e) =>
              setRegisterForm({ ...registerForm, email: e.target.value })
            }
          />

          <input
            type="password"
            placeholder="Password"
            className="w-full mb-3 p-3 rounded bg-black/30"
            value={registerForm.password}
            onChange={(e) =>
              setRegisterForm({ ...registerForm, password: e.target.value })
            }
          />

          <input
            type="password"
            placeholder="Confirm Password"
            className="w-full mb-4 p-3 rounded bg-black/30"
            value={registerForm.confirmPassword}
            onChange={(e) =>
              setRegisterForm({
                ...registerForm,
                confirmPassword: e.target.value,
              })
            }
          />

          <button className="w-full bg-purple-600 py-3 rounded font-semibold">
            Create Account
          </button>

          <p className="mt-4 text-center text-sm">
            Already registered?{' '}
            <button
              type="button"
              onClick={() => setCurrentPage('login')}
              className="text-blue-400"
            >
              Login
            </button>
          </p>
        </form>
      </div>
    );
  }

  /* ================= MAIN APP ================= */
  return (
    <div className="min-h-screen bg-slate-900 text-white p-8">
      <div className="flex justify-between mb-6">
        <h1 className="text-2xl font-bold">DeepTrust Dashboard</h1>
        <button
          onClick={handleLogout}
          className="bg-red-500/20 px-4 py-2 rounded"
        >
          Logout
        </button>
      </div>

      {!file && (
        <div
          onClick={() => fileInputRef.current.click()}
          className="border-2 border-dashed p-16 rounded-xl text-center cursor-pointer"
        >
          <Upload className="mx-auto mb-4" />
          <p>Click to upload image or video</p>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={handleFileSelect}
          />
        </div>
      )}

      {file && (
        <div className="grid md:grid-cols-2 gap-6">
          <div>
            {preview && (
              <img src={preview} alt="preview" className="rounded-xl" />
            )}
            <button
              onClick={analyzeMedia}
              disabled={analyzing}
              className="mt-4 w-full bg-blue-600 py-3 rounded"
            >
              {analyzing ? 'Analyzing...' : 'Analyze'}
            </button>
          </div>

          <div>
            {results ? (
              <>
                <h2 className="text-xl font-bold mb-2">
                  Verdict:{' '}
                  <span className={confidenceColor(results.confidence)}>
                    {results.isDeepfake ? 'Deepfake' : 'Authentic'}
                  </span>
                </h2>
                <p>Confidence: {(results.confidence * 100).toFixed(2)}%</p>

                <button
                  onClick={downloadReport}
                  className="mt-4 bg-green-600 px-4 py-2 rounded"
                >
                  Download Report
                </button>
              </>
            ) : (
              <p className="text-gray-400">
                Upload media and run analysis
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// export default DeepTrustApp;
export default Login;