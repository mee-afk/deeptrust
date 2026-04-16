import axios from 'axios';
import {
  BarChart3, Brain, CheckCircle,
  Eye,
  FlaskConical,
  Layers, Upload, XCircle
} from 'lucide-react';
import { useRef, useState } from 'react';

// ── Config ────────────────────────────────────────────────────────────────────
const GATEWAY_URL = 'http://localhost:8010';
const AUTH_URL    = 'http://localhost:8001';

const DeepTrustDetector = () => {
  const [file,          setFile]          = useState(null);
  const [preview,       setPreview]       = useState(null);
  const [analyzing,     setAnalyzing]     = useState(false);
  const [results,       setResults]       = useState(null);
  const [activeTab,     setActiveTab]     = useState('overview');
  const [token,         setToken]         = useState('');
  const [modelVersion,  setModelVersion]  = useState('v2');   // 'v1' or 'v2'
  const [gradcamView,   setGradcamView]   = useState('xceptionnet'); // 'mesonet' or 'xceptionnet'
  const [error,         setError]         = useState(null);
  const fileInputRef = useRef(null);

  // ── Auto-login ──────────────────────────────────────────────────────────────
  useState(() => {
    const autoLogin = async () => {
      try {
        const formData = new URLSearchParams();
        formData.append('username', 'jane@test.com');
        formData.append('password', 'TestPass123');
        const response = await axios.post(`${AUTH_URL}/token`, formData);
        setToken(response.data.access_token);
      } catch (err) {
        console.warn('Auto-login failed — continuing without auth:', err.message);
      }
    };
    autoLogin();
  }, []);

  // ── File selection ──────────────────────────────────────────────────────────
  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;
    const isMedia = selectedFile.type.startsWith('image/') ||
                    selectedFile.type.startsWith('video/');
    if (!isMedia) return;

    setFile(selectedFile);
    setResults(null);
    setError(null);

    const reader = new FileReader();
    reader.onloadend = () => setPreview(reader.result);
    reader.readAsDataURL(selectedFile);
  };

  // ── Analysis ────────────────────────────────────────────────────────────────
  const analyzeMedia = async () => {
    if (!file) return;
    setAnalyzing(true);
    setError(null);
    setResults(null);

    try {
      // Optional: upload to Analysis Service for DB record
      if (token) {
        const uploadData = new FormData();
        uploadData.append('file', file);
        try {
          await axios.post(`${GATEWAY_URL}/api/upload`, uploadData, {
            headers: { Authorization: `Bearer ${token}` }
          });
        } catch (uploadErr) {
          console.warn('Upload to analysis service failed (non-fatal):', uploadErr.message);
        }
      }

      // Main prediction via Gateway
      const predictData = new FormData();
      predictData.append('file', file);

      const response = await axios.post(
        `${GATEWAY_URL}/api/analyze?model_version=${modelVersion}&gradcam=true`,
        predictData
      );

      const data = response.data;
      setResults(transformResponse(data, modelVersion));

    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setError(`Analysis failed: ${detail}`);
      console.error('Analysis error:', err);
    } finally {
      setAnalyzing(false);
    }
  };

  // ── Transform backend response to UI shape ──────────────────────────────────
  const transformResponse = (data, version) => {
  const isV2 = version === 'v2';

  // API returns 'verdict' string, not 'is_deepfake' boolean
  const isFake = data.verdict === 'FAKE' || data.is_deepfake === true;

  // Use confidence directly from API — already correct
  const confidence = data.confidence ?? data.confidence_score ?? 0.5;
  const displayConf = isFake ? confidence : 1.0 - (data.ensemble_score ?? 0.5);

  return {
    isDeepfake:        isFake,
    verdict:           isFake ? 'FAKE' : 'REAL',
    confidence:        Math.max(0, Math.min(1, displayConf)),
    confidencePct:     data.confidence_pct ?? `${(displayConf * 100).toFixed(2)}%`,
    ensembleScore:     data.ensemble_score,
    calibrationActive: data.calibration_active ?? false,
    modelVersion:      version,
    explanation:       data.explanation ?? '',

    models: {
      mesonet: {
        score:   data.model_scores?.mesonet  ?? data.mesonet?.score  ?? 0.5,
        weight:  data.ensemble_weights?.mesonet  ?? data.mesonet?.weight  ?? (isV2 ? 0.55 : 0.30),
        version: isV2 ? 'V2 (trained)' : 'V1 (heuristic)',
        dfdc:    isV2 ? '93.41%' : 'N/A'
      },
      xception: {
        score:   data.model_scores?.xception ?? data.xceptionnet?.score ?? 0.5,
        weight:  data.ensemble_weights?.xception ?? data.xceptionnet?.weight ?? (isV2 ? 0.45 : 0.35),
        version: isV2 ? 'V2 (trained)' : 'V1 (heuristic)',
        dfdc:    isV2 ? '93.20%' : 'N/A'
      },
      ...(isV2 ? {} : {
        frequency: {
          score:   data.model_scores?.frequency  ?? 0.5,
          weight:  data.ensemble_weights?.frequency  ?? 0.20,
          version: 'V1 (heuristic)',
          dfdc:    'N/A'
        },
        biological: {
          score:   data.model_scores?.biological ?? 0.5,
          weight:  data.ensemble_weights?.biological ?? 0.15,
          version: 'V1 (heuristic)',
          dfdc:    'N/A'
        }
      })
    },

    ensembleInfo: data.ensemble_info ?? null,
    gradcam:      data.gradcam ?? null,
    raw:          data
  };
};
  // const transformResponse = (data, version) => {
  //   const isV2   = version === 'v2';
  //   const isFake = data.is_deepfake;

  //   // Confidence — V2 uses calibrated, V1 uses raw
  //   const confidence = isV2
  //     ? (data.calibrated_score ?? data.confidence_score ?? data.ensemble_score)
  //     : data.ensemble_score;

  //   // Displayed confidence is always P(correct verdict)
  //   const displayConf = isFake ? confidence : (isV2 ? 1 - (data.calibrated_score ?? data.ensemble_score) : 1 - confidence);

  //   return {
  //     isDeepfake:       isFake,
  //     verdict:          isFake ? 'FAKE' : 'REAL',
  //     confidence:       Math.max(0, Math.min(1, displayConf)),
  //     confidencePct:    data.confidence_pct ?? `${(Math.max(0, Math.min(1, displayConf)) * 100).toFixed(2)}%`,
  //     ensembleScore:    data.ensemble_score,
  //     calibrationActive: data.calibration_active ?? false,
  //     modelVersion:     version,
  //     explanation:      data.explanation ?? '',

  //     // Model scores
  //     models: {
  //       mesonet: {
  //         score:   data.model_scores?.mesonet  ?? 0.5,
  //         weight:  data.ensemble_weights?.mesonet  ?? (isV2 ? 0.55 : 0.30),
  //         version: isV2 ? 'V2 (trained)' : 'V1 (heuristic)',
  //         dfdc:    isV2 ? '93.41%' : 'N/A'
  //       },
  //       xception: {
  //         score:   data.model_scores?.xception ?? 0.5,
  //         weight:  data.ensemble_weights?.xception ?? (isV2 ? 0.45 : 0.35),
  //         version: isV2 ? 'V2 (trained)' : 'V1 (heuristic)',
  //         dfdc:    isV2 ? '93.20%' : 'N/A'
  //       },
  //       ...(isV2 ? {} : {
  //         frequency: {
  //           score:   data.model_scores?.frequency  ?? 0.5,
  //           weight:  data.ensemble_weights?.frequency  ?? 0.20,
  //           version: 'V1 (heuristic)',
  //           dfdc:    'N/A'
  //         },
  //         biological: {
  //           score:   data.model_scores?.biological ?? 0.5,
  //           weight:  data.ensemble_weights?.biological ?? 0.15,
  //           version: 'V1 (heuristic)',
  //           dfdc:    'N/A'
  //         }
  //       })
  //     },

  //     // Ensemble info
  //     ensembleInfo: data.ensemble_info ?? null,

  //     // Grad-CAM (V2 only)
  //     gradcam: data.gradcam ?? null,

  //     // Raw backend data for debugging
  //     raw: data
  //   };
  // };



  // ── UI helpers ──────────────────────────────────────────────────────────────
  const getVerdictColor = (isFake, conf) => {
    if (isFake)  return conf > 0.8 ? 'text-red-500'    : 'text-orange-400';
    return conf  > 0.8 ? 'text-green-400'   : 'text-emerald-300';
  };

  const getConfBg = (isFake, conf) => {
    if (isFake)  return conf > 0.8 ? 'bg-red-900/40 border-red-500/50'    : 'bg-orange-900/40 border-orange-500/50';
    return conf  > 0.8 ? 'bg-green-900/40 border-green-500/50' : 'bg-emerald-900/40 border-emerald-500/50';
  };

  const getBarColor = (score) =>
    score > 0.7 ? 'from-red-500 to-red-600'
    : score > 0.4 ? 'from-yellow-500 to-orange-500'
    : 'from-green-500 to-emerald-500';

  // ─────────────────────────────────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 text-white">

      {/* ── Header ── */}
      <div className="bg-black/30 backdrop-blur-sm border-b border-white/10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">DeepTrust</h1>
            <p className="text-sm text-blue-200">Explainable AI Deepfake Detection</p>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <span className={token ? 'text-green-400' : 'text-yellow-400'}>
              {token ? '✓ Authenticated' : '⚠ No Auth'}
            </span>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">

        {/* ── Model Selector ── */}
        <div className="mb-8 flex justify-center">
          <div className="bg-black/30 rounded-2xl p-1 border border-white/10 flex gap-1">
            <button
              onClick={() => { setModelVersion('v2'); setResults(null); }}
              className={`px-6 py-3 rounded-xl font-semibold transition-all flex items-center gap-2 ${
                modelVersion === 'v2'
                  ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg'
                  : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <Brain className="w-4 h-4" />
              DeepTrust V2
              <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full">95.52% DFDC</span>
            </button>
            <button
              onClick={() => { setModelVersion('v1'); setResults(null); }}
              className={`px-6 py-3 rounded-xl font-semibold transition-all flex items-center gap-2 ${
                modelVersion === 'v1'
                  ? 'bg-white/10 text-white border border-white/20'
                  : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <FlaskConical className="w-4 h-4" />
              Classic Models
              <span className="text-xs bg-white/10 px-2 py-0.5 rounded-full">Baseline</span>
            </button>
          </div>
        </div>

        {/* Model version info banner */}
        <div className={`mb-6 p-4 rounded-xl border text-sm ${
          modelVersion === 'v2'
            ? 'bg-blue-900/30 border-blue-500/30 text-blue-200'
            : 'bg-gray-800/50 border-gray-600/30 text-gray-300'
        }`}>
          {modelVersion === 'v2' ? (
            <p>
              <span className="font-semibold text-blue-300">DeepTrust V2</span> — 
              MesoNet + XceptionNet trained on FaceForensics++ (210,952 frames), 
              cross-validated on DFDC (39,428 unseen frames). 
              Platt-calibrated confidence. Grad-CAM XAI included.
            </p>
          ) : (
            <p>
              <span className="font-semibold text-gray-200">Classic Models (Baseline)</span> — 
              Lightweight heuristic analysis using texture variance, HOG features, 
              FFT/DCT coefficients, and facial symmetry. 
              Kept for academic comparison — no deep learning training involved.
            </p>
          )}
        </div>

        {/* ── Upload Zone (shown when no file selected) ── */}
        {!file && (
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold mb-4 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
              Verify Media Authenticity
            </h2>
            <p className="text-blue-200 mb-8 text-lg">
              Upload an image or video for AI-powered deepfake detection
            </p>
            <div
              onClick={() => fileInputRef.current?.click()}
              className="max-w-2xl mx-auto border-2 border-dashed border-blue-400/50 rounded-2xl p-16 hover:border-blue-400 hover:bg-white/5 transition-all cursor-pointer"
            >
              <Upload className="w-16 h-16 mx-auto mb-4 text-blue-400" />
              <p className="text-xl mb-2">Click to upload media</p>
              <p className="text-sm text-blue-300">Supports JPG, PNG, MP4, AVI</p>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*,video/*"
                onChange={handleFileSelect}
                className="hidden"
              />
            </div>

            <div className="grid md:grid-cols-4 gap-6 mt-12">
              {[
                { icon: Brain,    title: 'Trained CNNs',       desc: 'MesoNet V2 + XceptionNet V2' },
                { icon: BarChart3, title: 'Cross-validated',   desc: 'DFDC 39,428 unseen frames' },
                { icon: Eye,      title: 'Grad-CAM XAI',       desc: 'Visualize altered regions' },
                { icon: Layers,   title: 'Platt Calibration',  desc: '81,620 image calibration' }
              ].map((f, i) => (
                <div key={i} className="bg-white/5 rounded-xl p-6 border border-white/10">
                  <f.icon className="w-8 h-8 text-blue-400 mb-3 mx-auto" />
                  <h3 className="font-semibold mb-2">{f.title}</h3>
                  <p className="text-sm text-blue-300">{f.desc}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Analysis Interface ── */}
        {file && (
          <div className="grid lg:grid-cols-2 gap-8">

            {/* Preview + Grad-CAM Panel */}
            <div className="bg-white/5 backdrop-blur-sm rounded-2xl p-6 border border-white/10">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-semibold">Media Preview</h3>
                {results?.gradcam && (
                  <div className="flex gap-1 bg-black/30 rounded-lg p-1">
                    <button
                      onClick={() => setGradcamView('original')}
                      className={`px-3 py-1 text-xs rounded transition-all ${
                        gradcamView === 'original' ? 'bg-blue-500 text-white' : 'text-gray-400'
                      }`}
                    >Original</button>
                    <button
                      onClick={() => setGradcamView('mesonet')}
                      className={`px-3 py-1 text-xs rounded transition-all ${
                        gradcamView === 'mesonet' ? 'bg-blue-500 text-white' : 'text-gray-400'
                      }`}
                    >MesoNet</button>
                    <button
                      onClick={() => setGradcamView('xceptionnet')}
                      className={`px-3 py-1 text-xs rounded transition-all ${
                        gradcamView === 'xceptionnet' ? 'bg-blue-500 text-white' : 'text-gray-400'
                      }`}
                    >XceptionNet</button>
                  </div>
                )}
              </div>

              {preview && (
                <div className="relative">
                  {/* Original preview */}
                  {(!results?.gradcam || gradcamView === 'original') && (
                    <img src={preview} alt="Preview" className="w-full rounded-xl" />
                  )}
                  {/* Grad-CAM overlays */}
                  {results?.gradcam && gradcamView === 'mesonet' && (
                    <div>
                      <img
                        src={`data:image/jpeg;base64,${results.gradcam.mesonet.image_base64}`}
                        alt="MesoNet Grad-CAM"
                        className="w-full rounded-xl"
                      />
                      <p className="text-xs text-center text-gray-400 mt-2">
                        {results.gradcam.mesonet.description}
                      </p>
                    </div>
                  )}
                  {results?.gradcam && gradcamView === 'xceptionnet' && (
                    <div>
                      <img
                        src={`data:image/jpeg;base64,${results.gradcam.xceptionnet.image_base64}`}
                        alt="XceptionNet Grad-CAM"
                        className="w-full rounded-xl"
                      />
                      <p className="text-xs text-center text-gray-400 mt-2">
                        {results.gradcam.xceptionnet.description}
                      </p>
                    </div>
                  )}
                  {/* Grad-CAM legend */}
                  {results?.gradcam && gradcamView !== 'original' && (
                    <div className="flex items-center gap-2 mt-2 text-xs text-gray-400">
                      <div className="flex gap-1">
                        <div className="w-3 h-3 rounded-sm bg-blue-500"/>
                        <span>Low</span>
                      </div>
                      <div className="flex gap-1">
                        <div className="w-3 h-3 rounded-sm bg-yellow-400"/>
                        <span>Medium</span>
                      </div>
                      <div className="flex gap-1">
                        <div className="w-3 h-3 rounded-sm bg-red-500"/>
                        <span>High — manipulation detected</span>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Action buttons */}
              <div className="flex gap-3 mt-4">
                <button
                  onClick={analyzeMedia}
                  disabled={analyzing}
                  className="flex-1 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed px-6 py-3 rounded-xl font-semibold transition-all"
                >
                  {analyzing
                    ? `Running ${modelVersion === 'v2' ? 'DeepTrust V2' : 'Classic'} Analysis...`
                    : 'Analyze Media'}
                </button>
                <button
                  onClick={() => { setFile(null); setPreview(null); setResults(null); setError(null); }}
                  className="px-6 py-3 bg-white/10 hover:bg-white/20 rounded-xl transition-all"
                >Clear</button>
              </div>

              {error && (
                <div className="mt-3 p-3 bg-red-900/40 border border-red-500/40 rounded-xl text-sm text-red-300">
                  {error}
                </div>
              )}
            </div>

            {/* Results Panel */}
            <div className="bg-white/5 backdrop-blur-sm rounded-2xl p-6 border border-white/10">
              <h3 className="text-xl font-semibold mb-4">Analysis Results</h3>

              {!results && !analyzing && (
                <div className="text-center py-12 text-blue-300">
                  Click "Analyze Media" to begin detection
                </div>
              )}

              {analyzing && (
                <div className="text-center py-12">
                  <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-400 mx-auto mb-4"/>
                  <p className="text-blue-300">
                    {modelVersion === 'v2'
                      ? 'Running DeepTrust V2 ensemble...'
                      : 'Running classic model analysis...'}
                  </p>
                  <p className="text-sm text-blue-400 mt-2">
                    {modelVersion === 'v2'
                      ? 'MesoNet V2 + XceptionNet V2 + Grad-CAM + Platt calibration'
                      : 'Texture + HOG + FFT + Biological analysis'}
                  </p>
                </div>
              )}

              {results && (
                <div className="space-y-5">

                  {/* Verdict Card */}
                  <div className={`p-5 rounded-xl border-2 ${getConfBg(results.isDeepfake, results.confidence)}`}>
                    <div className="flex items-center gap-3 mb-2">
                      {results.isDeepfake
                        ? <XCircle className="w-8 h-8 text-red-400"/>
                        : <CheckCircle className="w-8 h-8 text-green-400"/>}
                      <div>
                        <h4 className={`text-2xl font-bold ${getVerdictColor(results.isDeepfake, results.confidence)}`}>
                          {results.isDeepfake ? '⚠ DEEPFAKE DETECTED' : '✓ AUTHENTIC'}
                        </h4>
                        <p className="text-sm text-gray-300">
                          Confidence: <span className="font-bold text-white">{results.confidencePct}</span>
                          {results.calibrationActive && (
                            <span className="ml-2 text-xs bg-blue-500/30 text-blue-300 px-2 py-0.5 rounded-full">
                              Platt calibrated
                            </span>
                          )}
                        </p>
                      </div>
                    </div>
                    <div className="text-xs text-gray-400 mt-1">
                      Using: <span className="text-white font-medium">
                        {results.modelVersion === 'v2' ? 'DeepTrust V2 (Trained Ensemble)' : 'Classic Models (Baseline)'}
                      </span>
                    </div>
                  </div>

                  {/* Tabs */}
                  <div className="flex gap-2 border-b border-white/20">
                    {['overview', 'models', 'xai'].map(tab => (
                      <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`px-4 py-2 font-medium capitalize transition-colors ${
                          activeTab === tab
                            ? 'text-blue-400 border-b-2 border-blue-400'
                            : 'text-gray-400 hover:text-white'
                        }`}
                      >{tab}</button>
                    ))}
                  </div>

                  {/* Overview Tab */}
                  {activeTab === 'overview' && (
                    <div className="space-y-4">
                      <div className="bg-white/5 rounded-xl p-4">
                        <h5 className="font-semibold mb-3">Model Score Breakdown</h5>
                        <div className="space-y-3">
                          {Object.entries(results.models).map(([name, data]) => (
                            <div key={name}>
                              <div className="flex justify-between text-sm mb-1">
                                <span className="capitalize flex items-center gap-2">
                                  {name}
                                  <span className="text-xs text-gray-500">({data.version})</span>
                                </span>
                                <span className="font-medium">
                                  {(data.score * 100).toFixed(1)}%
                                  <span className="text-gray-500 ml-1">× {data.weight}</span>
                                </span>
                              </div>
                              <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                                <div
                                  className={`h-full bg-gradient-to-r ${getBarColor(data.score)} transition-all duration-700`}
                                  style={{ width: `${data.score * 100}%` }}
                                />
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* V2 performance info */}
                      {results.modelVersion === 'v2' && results.ensembleInfo && (
                        <div className="bg-blue-900/30 border border-blue-500/30 rounded-xl p-4 text-sm">
                          <h5 className="font-semibold text-blue-300 mb-2">
                            DeepTrust V2 — Validated Performance
                          </h5>
                          <div className="grid grid-cols-2 gap-2 text-xs text-blue-200">
                            <div>Accuracy: <span className="text-white font-medium">{results.ensembleInfo.accuracy}</span></div>
                            <div>Recall: <span className="text-white font-medium">{results.ensembleInfo.recall}</span></div>
                            <div>Specificity: <span className="text-white font-medium">{results.ensembleInfo.specificity}</span></div>
                            <div>AUC-ROC: <span className="text-white font-medium">{results.ensembleInfo.auc_roc}</span></div>
                          </div>
                          <p className="text-xs text-blue-300 mt-2">
                            Cross-validated on DFDC — never seen during training
                          </p>
                        </div>
                      )}

                      {/* V1 baseline note */}
                      {results.modelVersion === 'v1' && (
                        <div className="bg-gray-800/50 border border-gray-600/30 rounded-xl p-4 text-sm text-gray-300">
                          <h5 className="font-semibold text-gray-200 mb-1">Classic Models — Academic Baseline</h5>
                          <p className="text-xs">
                            Results from heuristic analysis without deep learning training.
                            Compare with DeepTrust V2 to see the improvement from trained models.
                          </p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Models Tab */}
                  {activeTab === 'models' && (
                    <div className="space-y-3">
                      {Object.entries(results.models).map(([name, data]) => (
                        <div key={name} className="bg-white/5 rounded-xl p-4">
                          <div className="flex justify-between items-center mb-1">
                            <h5 className="font-semibold capitalize">{name}</h5>
                            <span className={`text-sm font-bold ${
                              data.score > 0.5 ? 'text-red-400' : 'text-green-400'
                            }`}>
                              {(data.score * 100).toFixed(1)}%
                              <span className="text-xs text-gray-400 ml-1 font-normal">
                                {data.score > 0.5 ? 'FAKE' : 'REAL'}
                              </span>
                            </span>
                          </div>
                          <div className="flex gap-3 text-xs text-gray-400">
                            <span>Version: <span className="text-gray-200">{data.version}</span></span>
                            <span>Weight: <span className="text-gray-200">{(data.weight * 100).toFixed(0)}%</span></span>
                            {data.dfdc !== 'N/A' && (
                              <span>DFDC acc: <span className="text-blue-300">{data.dfdc}</span></span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* XAI Tab */}
                  {activeTab === 'xai' && (
                    <div className="space-y-4">
                      {results.explanation && (
                        <div className="bg-white/5 rounded-xl p-4">
                          <h5 className="font-semibold mb-2 flex items-center gap-2">
                            <Eye className="w-4 h-4 text-blue-400"/>
                            Explanation
                          </h5>
                          <p className="text-sm text-gray-300 leading-relaxed">
                            {results.explanation}
                          </p>
                        </div>
                      )}

                      {results.gradcam ? (
                        <div className="bg-white/5 rounded-xl p-4">
                          <h5 className="font-semibold mb-3">Grad-CAM Heatmaps</h5>
                          <p className="text-xs text-gray-400 mb-3">
                            {results.gradcam.note}
                          </p>
                          <p className="text-xs text-gray-400">
                            Use the heatmap toggle above the image to switch between
                            MesoNet and XceptionNet activation maps.
                            Red/yellow regions show where each model detected manipulation.
                          </p>
                          <div className="grid grid-cols-2 gap-2 mt-3">
                            <div className="text-center">
                              <img
                                src={`data:image/jpeg;base64,${results.gradcam.mesonet.image_base64}`}
                                alt="MesoNet heatmap"
                                className="w-full rounded-lg"
                              />
                              <p className="text-xs text-gray-400 mt-1">MesoNet</p>
                            </div>
                            <div className="text-center">
                              <img
                                src={`data:image/jpeg;base64,${results.gradcam.xceptionnet.image_base64}`}
                                alt="XceptionNet heatmap"
                                className="w-full rounded-lg"
                              />
                              <p className="text-xs text-gray-400 mt-1">XceptionNet</p>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="bg-white/5 rounded-xl p-4 text-center text-gray-400 text-sm">
                          {results.modelVersion === 'v1'
                            ? 'Grad-CAM XAI is only available with DeepTrust V2. Switch to V2 to see heatmaps.'
                            : 'Grad-CAM not available for this result.'}
                        </div>
                      )}
                    </div>
                  )}

                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DeepTrustDetector;