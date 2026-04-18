import axios from 'axios';
import {
  AlertCircle,
  BarChart3, Brain,
  Eye,
  FlaskConical,
  Info,
  Layers,
  ShieldAlert,
  ShieldCheck,
  Upload
} from 'lucide-react';
import { useRef, useState } from 'react';

const GATEWAY_URL = 'http://localhost:8010';
const AUTH_URL    = 'http://localhost:8001';

const DeepTrustDetector = () => {
  const [file,         setFile]         = useState(null);
  const [preview,      setPreview]      = useState(null);
  const [analyzing,    setAnalyzing]    = useState(false);
  const [results,      setResults]      = useState(null);
  const [activeTab,    setActiveTab]    = useState('overview');
  const [token,        setToken]        = useState('');
  const [modelVersion, setModelVersion] = useState('v2');
  const [gradcamView,  setGradcamView]  = useState('xceptionnet');
  const [error,        setError]        = useState(null);
  const fileInputRef = useRef(null);

  useState(() => {
    const autoLogin = async () => {
      try {
        const formData = new URLSearchParams();
        formData.append('username', 'jane@test.com');
        formData.append('password', 'TestPass123');
        const response = await axios.post(`${AUTH_URL}/token`, formData);
        setToken(response.data.access_token);
      } catch (err) {
        console.warn('Auth not available');
      }
    };
    autoLogin();
  }, []);

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;
    const isMedia = selectedFile.type.startsWith('image/') || selectedFile.type.startsWith('video/');
    if (!isMedia) return;
    setFile(selectedFile);
    setResults(null);
    setError(null);
    setActiveTab('overview');
    const reader = new FileReader();
    reader.onloadend = () => setPreview(reader.result);
    reader.readAsDataURL(selectedFile);
  };

  const analyzeMedia = async () => {
    if (!file) return;
    setAnalyzing(true);
    setError(null);
    setResults(null);
    try {
      if (token) {
        const uploadData = new FormData();
        uploadData.append('file', file);
        try {
          await axios.post(`${GATEWAY_URL}/api/upload`, uploadData, {
            headers: { Authorization: `Bearer ${token}` }
          });
        } catch (e) { /* non-fatal */ }
      }
      const predictData = new FormData();
      predictData.append('file', file);
      const response = await axios.post(
        `${GATEWAY_URL}/api/analyze?model_version=${modelVersion}&gradcam=true`,
        predictData
      );
      setResults(transformResponse(response.data, modelVersion));
    } catch (err) {
      setError(`Analysis failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setAnalyzing(false);
    }
  };

  const transformResponse = (data, version) => {

    

    // NO_FACE — image has no human face detected
    if (data.error === 'no_face_detected' || data.verdict === 'NO_FACE') {
      return {
        isDeepfake:        false,
        verdict:           'NO_FACE',
        noFace:            true,
        confidence:        0,
        confidencePct:     'N/A',
        ensembleScore:     0,
        calibrationActive: false,
        modelVersion:      version,
        explanation:       data.explanation,
        mesoFakeScore:     0, xceptFakeScore: 0,
        mesoRealPct:       '0', xceptRealPct: '0',
        mesoFakePct:       '0', xceptFakePct: '0',
        models: {
          mesonet:  { score: 0, weight: 0.55, version: 'V2', dfdc: '93.41%' },
          xception: { score: 0, weight: 0.45, version: 'V2', dfdc: '93.20%' }
        },
        gradcam:      null,
        ensembleInfo: null,
        raw:          data
      };
    }

    // ── Video response ──────────────────────────────────────────────────
    if (data.frames_analyzed !== undefined) {
      const isFake = data.verdict === 'FAKE';
      const confidence = data.confidence ?? 0.5;
      return {
        isDeepfake:           isFake,
        verdict:              isFake ? 'FAKE' : 'REAL',
        confidence:           confidence,
        confidencePct:        `${(confidence * 100).toFixed(2)}%`,
        ensembleScore:        data.ensemble_score_mean ?? 0,
        calibrationActive:    data.calibration_active ?? false,
        modelVersion:         version,
        explanation:          data.explanation ?? '',
        isVideo:              true,
        framesAnalyzed:       data.frames_analyzed,
        ensembleMax:          data.ensemble_score_max,
        singleFrameTriggered: data.single_frame_triggered,
        mesoFakeScore:        data.mesonet?.mean_score ?? 0.5,
        xceptFakeScore:       data.xceptionnet?.mean_score ?? 0.5,
        mesoFakePct:          ((data.mesonet?.mean_score ?? 0.5) * 100).toFixed(1),
        xceptFakePct:         ((data.xceptionnet?.mean_score ?? 0.5) * 100).toFixed(1),
        mesoRealPct:          ((1 - (data.mesonet?.mean_score ?? 0.5)) * 100).toFixed(1),
        xceptRealPct:         ((1 - (data.xceptionnet?.mean_score ?? 0.5)) * 100).toFixed(1),
        models: {
          mesonet:  { score: data.mesonet?.mean_score  ?? 0.5, weight: 0.55, version: 'V2 (trained)', dfdc: '93.41%' },
          xception: { score: data.xceptionnet?.mean_score ?? 0.5, weight: 0.45, version: 'V2 (trained)', dfdc: '93.20%' }
        },
        gradcam:      null,
        frameResults: data.frame_results ?? [],
        raw:          data
      };
    }

    const isV2   = version === 'v2';
    const isFake = data.verdict === 'FAKE' || data.is_deepfake === true;
    const mesoScore  = data.model_scores?.mesonet  ?? data.mesonet?.score  ?? 0.5;
    const xceptScore = data.model_scores?.xception ?? data.xceptionnet?.score ?? 0.5;
    const confidence = data.confidence ?? 0.5;
    const displayConf = isFake ? confidence : 1.0 - (data.ensemble_score ?? 0.5);

    return {
      isDeepfake:        isFake,
      verdict:           isFake ? 'FAKE' : 'REAL',
      confidence:        Math.max(0, Math.min(1, displayConf)),
      confidencePct:     data.confidence_pct ?? `${(Math.max(0, Math.min(1, displayConf)) * 100).toFixed(2)}%`,
      ensembleScore:     data.ensemble_score ?? 0,
      calibrationActive: data.calibration_active ?? false,
      modelVersion:      version,
      explanation:       data.explanation ?? '',
      mesoFakeScore:     mesoScore,
      xceptFakeScore:    xceptScore,
      mesoRealPct:       ((1 - mesoScore) * 100).toFixed(1),
      xceptRealPct:      ((1 - xceptScore) * 100).toFixed(1),
      mesoFakePct:       (mesoScore * 100).toFixed(1),
      xceptFakePct:      (xceptScore * 100).toFixed(1),
      models: {
        mesonet: {
          score:   mesoScore,
          weight:  data.ensemble_weights?.mesonet ?? data.mesonet?.weight ?? (isV2 ? 0.55 : 0.30),
          version: isV2 ? 'V2 (trained)' : 'V1 (heuristic)',
          dfdc:    isV2 ? '93.41%' : 'N/A',
        },
        xception: {
          score:   xceptScore,
          weight:  data.ensemble_weights?.xception ?? data.xceptionnet?.weight ?? (isV2 ? 0.45 : 0.35),
          version: isV2 ? 'V2 (trained)' : 'V1 (heuristic)',
          dfdc:    isV2 ? '93.20%' : 'N/A',
        },
        ...(isV2 ? {} : {
          frequency:  { score: data.model_scores?.frequency  ?? 0.5, weight: 0.20, version: 'V1', dfdc: 'N/A' },
          biological: { score: data.model_scores?.biological ?? 0.5, weight: 0.15, version: 'V1', dfdc: 'N/A' }
        })
      },
      ensembleInfo: data.ensemble_info ?? null,
      gradcam:      data.gradcam ?? null,
      raw:          data
    };
  };

  const getFakeBarColor = (score) =>
    score > 0.7 ? 'from-red-500 to-red-600'
    : score > 0.4 ? 'from-yellow-500 to-orange-500'
    : 'from-green-500 to-emerald-500';

  const getScoreInterpretation = (score) => {
    if (score < 0.1) return 'Very confident — no manipulation detected';
    if (score < 0.3) return 'Low fake probability — likely authentic';
    if (score < 0.6) return 'Moderate signals — some artifacts present';
    return 'Strong manipulation indicators detected';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 text-white">

      {/* Header */}
      <div className="bg-black/40 backdrop-blur-sm border-b border-white/10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">DeepTrust</h1>
            <p className="text-xs text-blue-300 mt-0.5">Explainable AI Deepfake Detection System</p>
          </div>
          <span className={`text-xs ${token ? 'text-green-400' : 'text-gray-500'}`}>
            {token ? '● Authenticated' : '● No Auth'}
          </span>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">

        {/* Model Selector */}
        <div className="mb-6 flex justify-center">
          <div className="bg-black/30 rounded-2xl p-1 border border-white/10 flex gap-1">
            <button onClick={() => { setModelVersion('v2'); setResults(null); }}
              className={`px-6 py-3 rounded-xl font-semibold transition-all flex items-center gap-2 text-sm ${
                modelVersion === 'v2' ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg' : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}>
              <Brain className="w-4 h-4" />
              DeepTrust V2
              <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full font-normal">95.52% DFDC</span>
            </button>
            <button onClick={() => { setModelVersion('v1'); setResults(null); }}
              className={`px-6 py-3 rounded-xl font-semibold transition-all flex items-center gap-2 text-sm ${
                modelVersion === 'v1' ? 'bg-white/10 text-white border border-white/20' : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}>
              <FlaskConical className="w-4 h-4" />
              Classic Models
              <span className="text-xs bg-white/10 px-2 py-0.5 rounded-full font-normal">Baseline</span>
            </button>
          </div>
        </div>

        {/* Info Banner */}
        <div className={`mb-6 p-3 rounded-xl border text-xs ${
          modelVersion === 'v2' ? 'bg-blue-900/20 border-blue-500/20 text-blue-300' : 'bg-gray-800/40 border-gray-600/20 text-gray-400'
        }`}>
          {modelVersion === 'v2'
            ? '🎯 DeepTrust V2 — MesoNet + XceptionNet trained on FaceForensics++ (210,952 frames), cross-validated on DFDC (39,428 unseen frames). Platt-calibrated confidence. Grad-CAM XAI included.'
            : '🔬 Classic Models (Baseline) — Lightweight heuristic analysis for academic comparison. No deep learning training.'}
        </div>

        {/* Upload Zone */}
        {!file && (
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold mb-3 bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
              Verify Media Authenticity
            </h2>
            <p className="text-blue-200 mb-8">Upload an image or video for AI-powered deepfake detection with XAI explanations</p>
            <div onClick={() => fileInputRef.current?.click()}
              className="max-w-2xl mx-auto border-2 border-dashed border-blue-500/40 rounded-2xl p-16 hover:border-blue-400 hover:bg-white/3 transition-all cursor-pointer group">
              <Upload className="w-14 h-14 mx-auto mb-4 text-blue-400 group-hover:scale-110 transition-transform" />
              <p className="text-lg mb-1 font-medium">Click to upload media</p>
              <p className="text-sm text-blue-300/70">Supports JPG, PNG, MP4, AVI — pre-cropped face image recommended</p>
              <input ref={fileInputRef} type="file" accept="image/*,video/*" onChange={handleFileSelect} className="hidden" />
            </div>
            <div className="grid md:grid-cols-4 gap-4 mt-10">
              {[
                { icon: Brain,     title: 'Trained CNNs',     desc: 'MesoNet V2 + XceptionNet V2' },
                { icon: BarChart3, title: 'Cross-validated',  desc: 'DFDC 39,428 unseen frames' },
                { icon: Eye,       title: 'Grad-CAM XAI',     desc: 'Visualize decision regions' },
                { icon: Layers,    title: 'Platt Calibrated', desc: '81,620 image calibration' }
              ].map((f, i) => (
                <div key={i} className="bg-white/4 rounded-xl p-5 border border-white/8 text-center">
                  <f.icon className="w-7 h-7 text-blue-400 mb-2 mx-auto" />
                  <h3 className="font-semibold text-sm mb-1">{f.title}</h3>
                  <p className="text-xs text-blue-300/70">{f.desc}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Analysis Interface */}
        {file && (
          <div className="grid lg:grid-cols-2 gap-6">

            {/* Left — Preview */}
            <div className="bg-white/4 backdrop-blur-sm rounded-2xl p-5 border border-white/10">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-sm">Media Preview</h3>
                {results?.gradcam && (
                  <div className="flex gap-1 bg-black/30 rounded-lg p-1 text-xs">
                    {['original', 'mesonet', 'xceptionnet'].map(v => (
                      <button key={v} onClick={() => setGradcamView(v)}
                        className={`px-2.5 py-1 rounded capitalize transition-all ${
                          gradcamView === v ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
                        }`}>
                        {v === 'xceptionnet' ? 'Xcept' : v === 'mesonet' ? 'Meso' : 'Original'}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* {preview && (
                <div className="relative rounded-xl overflow-hidden">
                  {(!results?.gradcam || gradcamView === 'original') && (
                    <img src={preview} alt="Preview" className="w-full rounded-xl" />
                  )}
                  
                  {results?.gradcam && gradcamView === 'mesonet' && (
                    <img src={`data:image/jpeg;base64,${results.gradcam.mesonet.image_base64}`} alt="MesoNet Grad-CAM" className="w-full rounded-xl" />
                  )}
                  {results?.gradcam && gradcamView === 'xceptionnet' && (
                    <img src={`data:image/jpeg;base64,${results.gradcam.xceptionnet.image_base64}`} alt="XceptionNet Grad-CAM" className="w-full rounded-xl" />
                  )}
                  {results && !results.noFace && (
                    <div className={`absolute top-3 right-3 px-3 py-1.5 rounded-lg text-xs font-bold border backdrop-blur-sm ${
                      results.isDeepfake ? 'bg-red-900/80 border-red-500/60 text-red-300' : 'bg-green-900/80 border-green-500/60 text-green-300'
                    }`}>
                      {results.isDeepfake ? '⚠ FAKE' : '✓ REAL'}
                    </div>
                  )}
                  {results?.noFace && (
                    <div className="absolute top-3 right-3 px-3 py-1.5 rounded-lg text-xs font-bold border backdrop-blur-sm bg-yellow-900/80 border-yellow-500/60 text-yellow-300">
                      ⚠ NO FACE
                    </div>
                  )}
                </div>
              )} */}
              {preview && (
                <div className="relative rounded-xl overflow-hidden">

                  {/*  IMAGE PREVIEW */}
                  {file?.type.startsWith('image/') && (
                    <>
                      {(!results?.gradcam || gradcamView === 'original') && (
                        <img src={preview} alt="Preview" className="w-full rounded-xl" />
                      )}

                      {results?.gradcam && gradcamView === 'mesonet' && (
                        <img
                          src={`data:image/jpeg;base64,${results.gradcam.mesonet.image_base64}`}
                          alt="MesoNet Grad-CAM"
                          className="w-full rounded-xl"
                        />
                      )}

                      {results?.gradcam && gradcamView === 'xceptionnet' && (
                        <img
                          src={`data:image/jpeg;base64,${results.gradcam.xceptionnet.image_base64}`}
                          alt="XceptionNet Grad-CAM"
                          className="w-full rounded-xl"
                        />
                      )}
                    </>
                  )}

                  {/*  VIDEO PREVIEW */}
                  {file?.type.startsWith('video/') && (
                    <video
                      src={preview}
                      controls
                      className="w-full rounded-xl"
                    />
                  )}

                  {/* Verdict badge */}
                  {results && !results.noFace && (
                    <div className={`absolute top-3 right-3 px-3 py-1.5 rounded-lg text-xs font-bold border backdrop-blur-sm ${
                      results.isDeepfake
                        ? 'bg-red-900/80 border-red-500/60 text-red-300'
                        : 'bg-green-900/80 border-green-500/60 text-green-300'
                    }`}>
                      {results.isDeepfake ? '⚠ FAKE' : '✓ REAL'}
                    </div>
                  )}

                  {/* NO FACE badge */}
                  {results?.noFace && (
                    <div className="absolute top-3 right-3 px-3 py-1.5 rounded-lg text-xs font-bold border backdrop-blur-sm bg-yellow-900/80 border-yellow-500/60 text-yellow-300">
                      ⚠ NO FACE
                    </div>
                  )}

                </div>
              )}

              {/* Grad-CAM context note */}
              {results?.gradcam && gradcamView !== 'original' && (
                <div className="mt-3 space-y-2">
                  <div className="flex items-center gap-3 text-xs text-gray-500">
                    <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-sm bg-blue-500 opacity-60"/><span>Low</span></div>
                    <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-sm bg-yellow-400 opacity-60"/><span>Medium</span></div>
                    <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-sm bg-red-500 opacity-60"/><span>High attention</span></div>
                  </div>
                  <p className="text-xs text-gray-600 leading-relaxed">
                    {results.isDeepfake
                      ? '🔴 Red/yellow areas indicate where the model found manipulation artifacts — face boundaries, texture inconsistencies, or lighting anomalies.'
                      : '🔵 For authentic images, warm colors show where the model paid close attention and found NO manipulation. High attention ≠ manipulation detected.'}
                  </p>
                </div>
              )}

              <div className="flex gap-3 mt-4">
                <button onClick={analyzeMedia} disabled={analyzing}
                  className="flex-1 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 px-6 py-3 rounded-xl font-semibold text-sm transition-all">
                  {analyzing ? 'Analyzing...' : 'Analyze Media'}
                </button>
                <button onClick={() => { setFile(null); setPreview(null); setResults(null); setError(null); }}
                  className="px-5 py-3 bg-white/8 hover:bg-white/15 rounded-xl text-sm transition-all">
                  Clear
                </button>
              </div>
              {error && <div className="mt-3 p-3 bg-red-900/30 border border-red-500/30 rounded-xl text-xs text-red-300">{error}</div>}
            </div>

            {/* Right — Results */}
            <div className="bg-white/4 backdrop-blur-sm rounded-2xl p-5 border border-white/10">
              <h3 className="font-semibold mb-4 text-sm">Analysis Results</h3>

              {!results && !analyzing && (
                <div className="text-center py-16 text-gray-500 text-sm">Click "Analyze Media" to begin</div>
              )}

              {analyzing && (
                <div className="text-center py-16">
                  <div className="animate-spin rounded-full h-14 w-14 border-b-2 border-blue-500 mx-auto mb-4"/>
                  <p className="text-blue-300 text-sm">Running ensemble analysis...</p>
                  <p className="text-xs text-gray-500 mt-1">MesoNet V2 + XceptionNet V2 + Grad-CAM</p>
                </div>
              )}

              {results && (
                <div className="space-y-4">

                  {/* Verdict */}
                  {results.noFace ? (
                    /* ── NO FACE card ── */
                    <div className="p-4 rounded-xl border-2 bg-yellow-900/30 border-yellow-500/50">
                      <div className="flex items-start gap-3">
                        <AlertCircle className="w-7 h-7 text-yellow-400 flex-shrink-0 mt-0.5" />
                        <div>
                          <h4 className="text-lg font-bold text-yellow-400">⚠ NO FACE DETECTED</h4>
                          <p className="text-sm text-gray-300 mt-0.5">{results.explanation}</p>
                          <p className="text-xs text-gray-500 mt-1">
                            DeepTrust analyzes human faces only. Please upload a photo containing a clearly visible human face.
                          </p>
                        </div>
                      </div>
                    </div>
                  ) : (
                    /* ── FAKE / REAL card ── */
                    <div className={`p-4 rounded-xl border-2 ${
                      results.isDeepfake ? 'bg-red-900/30 border-red-500/50' : 'bg-green-900/30 border-green-500/50'
                    }`}>
                      <div className="flex items-start gap-3">
                        {results.isDeepfake
                          ? <ShieldAlert className="w-7 h-7 text-red-400 flex-shrink-0"/>
                          : <ShieldCheck className="w-7 h-7 text-green-400 flex-shrink-0"/>}
                        <div>
                          <h4 className={`text-lg font-bold ${results.isDeepfake ? 'text-red-400' : 'text-green-400'}`}>
                            {results.isDeepfake ? '⚠ DEEPFAKE DETECTED' : '✓ AUTHENTIC IMAGE'}
                          </h4>
                          <p className="text-sm text-gray-300 mt-0.5">
                            Confidence: <span className="font-bold text-white">{results.confidencePct}</span>
                            {results.calibrationActive && (
                              <span className="ml-2 text-xs bg-blue-500/25 text-blue-300 px-2 py-0.5 rounded-full">Platt calibrated</span>
                            )}
                          </p>
                          <p className="text-xs text-gray-500 mt-0.5">
                            {results.modelVersion === 'v2' ? 'DeepTrust V2 (Trained Ensemble)' : 'Classic Models (Baseline)'}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Tabs — hide for NO_FACE since there's no data to show */}
                  {!results.noFace && (
                    <>
                      <div className="flex gap-1 border-b border-white/10">
                        {['overview', 'models', 'xai'].map(tab => (
                          <button key={tab} onClick={() => setActiveTab(tab)}
                            className={`px-4 py-2 text-sm font-medium capitalize transition-colors ${
                              activeTab === tab ? 'text-blue-400 border-b-2 border-blue-400' : 'text-gray-500 hover:text-gray-300'
                            }`}>{tab}</button>
                        ))}
                      </div>

                      {/* OVERVIEW */}
                      {activeTab === 'overview' && (
                        <div className="space-y-3">
                          <div className="bg-black/20 rounded-xl p-4">
                            <div className="flex items-center gap-2 mb-4">
                              <h5 className="text-sm font-semibold text-gray-200">Model Fake-Probability Scores</h5>
                              <div className="group relative">
                                <Info className="w-3.5 h-3.5 text-gray-500 cursor-help"/>
                                <div className="hidden group-hover:block absolute left-0 top-5 z-10 bg-gray-800 border border-white/10 rounded-lg p-2 text-xs text-gray-300 w-56">
                                  Each score shows P(fake) — how likely the model thinks this image is a deepfake. 0% = definitely real, 100% = definitely fake. Threshold is 30%.
                                </div>
                              </div>
                            </div>

                            <div className="space-y-5">
                              {/* MesoNet score */}
                              <div>
                                <div className="flex justify-between items-end mb-1.5">
                                  <div>
                                    <span className="text-sm font-medium">MesoNet</span>
                                    <span className="text-xs text-gray-500 ml-2">weight {(results.models.mesonet.weight * 100).toFixed(0)}%</span>
                                  </div>
                                  <div className="text-right">
                                    <span className={`text-sm font-bold ${results.mesoFakeScore >= 0.3 ? 'text-red-400' : 'text-green-400'}`}>
                                      {results.mesoFakePct}% fake
                                    </span>
                                    <span className="text-xs text-gray-500 ml-1">({results.mesoRealPct}% real)</span>
                                  </div>
                                </div>
                                <div className="h-2.5 bg-white/8 rounded-full overflow-hidden">
                                  <div className={`h-full bg-gradient-to-r ${getFakeBarColor(results.mesoFakeScore)} transition-all duration-700`}
                                    style={{ width: `${results.mesoFakeScore * 100}%` }}/>
                                </div>
                                <p className="text-xs text-gray-600 mt-1">{getScoreInterpretation(results.mesoFakeScore)}</p>
                              </div>

                              {/* XceptionNet score */}
                              <div>
                                <div className="flex justify-between items-end mb-1.5">
                                  <div>
                                    <span className="text-sm font-medium">XceptionNet</span>
                                    <span className="text-xs text-gray-500 ml-2">weight {(results.models.xception.weight * 100).toFixed(0)}%</span>
                                  </div>
                                  <div className="text-right">
                                    <span className={`text-sm font-bold ${results.xceptFakeScore >= 0.3 ? 'text-red-400' : 'text-green-400'}`}>
                                      {results.xceptFakePct}% fake
                                    </span>
                                    <span className="text-xs text-gray-500 ml-1">({results.xceptRealPct}% real)</span>
                                  </div>
                                </div>
                                <div className="h-2.5 bg-white/8 rounded-full overflow-hidden">
                                  <div className={`h-full bg-gradient-to-r ${getFakeBarColor(results.xceptFakeScore)} transition-all duration-700`}
                                    style={{ width: `${results.xceptFakeScore * 100}%` }}/>
                                </div>
                                <p className="text-xs text-gray-600 mt-1">{getScoreInterpretation(results.xceptFakeScore)}</p>
                              </div>

                              {/* Ensemble */}
                              <div className="pt-3 border-t border-white/8">
                                <div className="flex justify-between items-center">
                                  <span className="text-sm font-semibold text-gray-200">Ensemble Score</span>
                                  <span className={`text-sm font-bold ${(results.ensembleScore ?? 0) >= 0.3 ? 'text-red-400' : 'text-green-400'}`}>
                                    {((results.ensembleScore ?? 0) * 100).toFixed(1)}% fake probability
                                  </span>
                                </div>
                                <p className="text-xs text-gray-600 mt-1">
                                  Weighted: {(results.models.mesonet.weight * 100).toFixed(0)}% MesoNet + {(results.models.xception.weight * 100).toFixed(0)}% XceptionNet · Decision threshold: 30%
                                </p>
                              </div>
                            </div>
                          </div>

                          {results.modelVersion === 'v2' && (
                            <div className="bg-blue-900/15 border border-blue-500/20 rounded-xl p-3 text-xs">
                              <p className="text-blue-300 font-medium mb-1.5">DeepTrust V2 — Validated Performance</p>
                              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-blue-200/70">
                                <span>DFDC Accuracy: <span className="text-white font-medium">95.52%</span></span>
                                <span>AUC-ROC: <span className="text-white font-medium">0.9927</span></span>
                                <span>Recall (fakes): <span className="text-white font-medium">95.48%</span></span>
                                <span>Specificity: <span className="text-white font-medium">95.56%</span></span>
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {/* MODELS */}
                      {activeTab === 'models' && (
                        <div className="space-y-3">
                          <div className="bg-amber-900/10 border border-amber-500/20 rounded-lg p-3 flex gap-2 text-xs text-amber-300/80">
                            <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5"/>
                            <span>Scores show P(fake) — probability of being a deepfake. Near 0% = confident real, near 100% = confident fake. Decision threshold is 30%.</span>
                          </div>
                          {Object.entries(results.models).map(([name, data]) => (
                            <div key={name} className="bg-black/20 rounded-xl p-4">
                              <div className="flex justify-between items-start mb-2">
                                <div>
                                  <h5 className="font-semibold text-sm">
                                    {name === 'xception' ? 'XceptionNet' : name.charAt(0).toUpperCase() + name.slice(1)}
                                  </h5>
                                  <p className="text-xs text-gray-500">{data.version} · Weight: {(data.weight * 100).toFixed(0)}%</p>
                                  {data.dfdc !== 'N/A' && <p className="text-xs text-blue-400">DFDC: {data.dfdc}</p>}
                                </div>
                                <div className="text-right">
                                  <p className={`text-base font-bold ${data.score >= 0.3 ? 'text-red-400' : 'text-green-400'}`}>
                                    {(data.score * 100).toFixed(1)}%
                                  </p>
                                  <p className="text-xs text-gray-500">fake probability</p>
                                  <span className={`text-xs font-bold px-2 py-0.5 rounded mt-0.5 inline-block ${
                                    data.score >= 0.3 ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'
                                  }`}>{data.score >= 0.3 ? 'FAKE' : 'REAL'}</span>
                                </div>
                              </div>
                              <div className="h-2 bg-white/8 rounded-full overflow-hidden">
                                <div className={`h-full bg-gradient-to-r ${getFakeBarColor(data.score)}`}
                                  style={{ width: `${data.score * 100}%` }}/>
                              </div>
                              <p className="text-xs text-gray-600 mt-1">{getScoreInterpretation(data.score)}</p>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* XAI */}
                      {activeTab === 'xai' && (
                        <div className="space-y-4">
                          {results.explanation && (
                            <div className="bg-black/20 rounded-xl p-4">
                              <h5 className="font-semibold mb-2 flex items-center gap-2 text-sm">
                                <Eye className="w-4 h-4 text-blue-400"/>
                                XAI Explanation
                              </h5>
                              <p className="text-sm text-gray-300 leading-relaxed">{results.explanation}</p>
                            </div>
                          )}

                          {/* Important note for real images */}
                          {!results.isDeepfake && results.gradcam && (
                            <div className="bg-blue-900/15 border border-blue-500/20 rounded-lg p-3 flex gap-2 text-xs text-blue-300/80">
                              <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5"/>
                              <span>
                                <strong className="text-blue-300">About Grad-CAM on authentic images:</strong> Warm colors (red/yellow) show regions the model examined closely — not regions where manipulation was found. The model inspected these areas and confirmed they are authentic. This is expected Grad-CAM behavior.
                              </span>
                            </div>
                          )}

                          {results.gradcam ? (
                            <div className="bg-black/20 rounded-xl p-4">
                              <h5 className="font-semibold mb-1 text-sm">Grad-CAM Activation Maps</h5>
                              <p className="text-xs text-gray-500 mb-3">
                                Gradient-weighted Class Activation Mapping — visualizes which regions influenced the model's decision.
                              </p>
                              <div className="grid grid-cols-2 gap-3">
                                <div className="text-center">
                                  <img src={`data:image/jpeg;base64,${results.gradcam.mesonet.image_base64}`}
                                    alt="MesoNet Grad-CAM" className="w-full rounded-lg border border-white/10"/>
                                  <div className="mt-1.5">
                                    <p className="text-xs font-medium text-gray-300">MesoNet V2</p>
                                    <p className="text-xs text-gray-600">Low-level texture artifacts</p>
                                    <p className={`text-xs font-bold mt-0.5 ${results.mesoFakeScore >= 0.3 ? 'text-red-400' : 'text-green-400'}`}>
                                      {results.mesoFakePct}% fake
                                    </p>
                                  </div>
                                </div>
                                <div className="text-center">
                                  <img src={`data:image/jpeg;base64,${results.gradcam.xceptionnet.image_base64}`}
                                    alt="XceptionNet Grad-CAM" className="w-full rounded-lg border border-white/10"/>
                                  <div className="mt-1.5">
                                    <p className="text-xs font-medium text-gray-300">XceptionNet V2</p>
                                    <p className="text-xs text-gray-600">High-level spatial patterns</p>
                                    <p className={`text-xs font-bold mt-0.5 ${results.xceptFakeScore >= 0.3 ? 'text-red-400' : 'text-green-400'}`}>
                                      {results.xceptFakePct}% fake
                                    </p>
                                  </div>
                                </div>
                              </div>
                              <div className="flex items-center justify-center gap-4 mt-3 text-xs text-gray-600">
                                <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-sm bg-blue-500 opacity-60"/><span>Low attention</span></div>
                                <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-sm bg-yellow-400 opacity-60"/><span>Medium</span></div>
                                <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-sm bg-red-500 opacity-60"/><span>High attention</span></div>
                              </div>
                            </div>
                          ) : (
                            <div className="bg-black/20 rounded-xl p-6 text-center text-gray-500 text-sm">
                              {results.modelVersion === 'v1' ? 'Grad-CAM XAI is only available with DeepTrust V2.' : 'Grad-CAM not available.'}
                            </div>
                          )}
                        </div>
                      )}
                    </>
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