/**
 * DeepTrust Frontend Application
 * =============================
 * This is the primary user interface for the DeepTrust Deepfake Detection System.
 * It provides a responsive dashboard for uploading media, performing AI-powered 
 * ensemble analysis, and visualizing XAI (Explainable AI) results via Grad-CAM.
 * 
 * Features:
 * - Multi-model ensemble analysis (MesoNet + XceptionNet).
 * - Support for both image and video media types.
 * - Grad-CAM visual heatmaps for spatial anomaly detection.
 * - Platt-calibrated confidence scores for production reliability.
 */

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

// Service mesh configuration for backend communication
const GATEWAY_URL = 'http://localhost:8010'; // Entry point for all API requests
const AUTH_URL    = 'http://localhost:8001'; // Direct link for identity operations

const DeepTrustDetector = () => {
  // ── Application State ──────────────────────────────────────────────────────
  
  // Media handling state
  const [file,         setFile]         = useState(null);    // The raw File object
  const [preview,      setPreview]      = useState(null);    // Data URL for local preview
  const [analyzing,    setAnalyzing]    = useState(false);   // Loading state for UI feedback
  const [results,      setResults]      = useState(null);    // Transformed API response
  const [activeTab,    setActiveTab]    = useState('overview'); // UI navigation state
  
  // Internal configurations and telemetry
  const [token,        setToken]        = useState('');      // Session JWT for authenticated uploads
  const [modelVersion, setModelVersion] = useState('v2');    // Selected detection pipeline ('v1' | 'v2')
  const [gradcamView,  setGradcamView]  = useState('xceptionnet'); // Active XAI heatmap layer
  const [error,        setError]        = useState(null);    // Error boundary state
  
  // UI References
  const fileInputRef = useRef(null);

  /**
   * Effect: Automatic Session Bootstrap
   * Temporarily performs an automatic login for development/quick-start purposes.
   * In a production deployment, this would be handled via the Login component.
   */
  useState(() => {
    const autoLogin = async () => {
      try {
        const formData = new URLSearchParams();
        formData.append('username', 'jane@test.com');
        formData.append('password', 'TestPass123');
        const response = await axios.post(`${AUTH_URL}/token`, formData);
        setToken(response.data.access_token);
      } catch (err) {
        console.warn('Authentication service temporarily unavailable; proceeding in guest mode.');
      }
    };
    autoLogin();
  }, []);

  /**
   * Handles local file selection and generates a visual preview.
   * @param {Event} e - The standard browser file input event.
   */
  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;

    // Validate that the media is supported by the backend pipeline
    const isMedia = selectedFile.type.startsWith('image/') || selectedFile.type.startsWith('video/');
    if (!isMedia) {
      setError('Unsupported file type. Please upload an image or video.');
      return;
    }

    // Reset application state for a new analysis session
    setFile(selectedFile);
    setResults(null);
    setError(null);
    setActiveTab('overview');

    // Generate non-persistent local preview for the feedback cycle
    const reader = new FileReader();
    reader.onloadend = () => setPreview(reader.result);
    reader.readAsDataURL(selectedFile);
  };

  /**
   * Orchestrates the media analysis sequence.
   * 1. Performs an optional authenticated upload to the Analysis Service.
   * 2. Triggers the inference engine via the API Gateway.
   * 3. Transforms and persists the detection results.
   */
  const analyzeMedia = async () => {
    if (!file) return;
    
    setAnalyzing(true);
    setError(null);
    setResults(null);
    
    try {
      // Step 1: Optional archival upload (if authenticated)
      if (token) {
        const uploadData = new FormData();
        uploadData.append('file', file);
        try {
          // Failure in archival upload is non-fatal to the inference process
          await axios.post(`${GATEWAY_URL}/api/upload`, uploadData, {
            headers: { Authorization: `Bearer ${token}` }
          });
        } catch (e) { 
          console.debug('Archival upload bypassed.');
        }
      }

      // Step 2: Core ML Inference Request
      const predictData = new FormData();
      predictData.append('file', file);
      
      const response = await axios.post(
        `${GATEWAY_URL}/api/analyze?model_version=${modelVersion}&gradcam=true`,
        predictData
      );

      // Step 3: Result transformation and state update
      setResults(transformResponse(response.data, modelVersion));
    } catch (err) {
      // Catch network or backend-level orchestration failures
      setError(`Analysis engine failure: ${err.response?.data?.detail || err.message}`);
    } finally {
      setAnalyzing(false);
    }
  };

  /**
   * Normalizes disparate backend responses into a unified, UI-ready model.
   * Handles individual frame-level results for videos and ensemble scoring for images.
   * 
   * @param {Object} data - Raw JSON response from the API Gateway.
   * @param {string} version - The model version used during inference.
   * @returns {Object} A sanitized results object.
   */
  const transformResponse = (data, version) => {
    // Scenario A: No human face detected in the provided media.
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

    // Scenario B: Detailed Video Temporal Analysis.
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
        mesoFakeScore:        data.mesonet?.score ?? 0.5,
        xceptFakeScore:       data.xceptionnet?.score ?? 0.5,
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

    // Scenario C: Single Image Static Analysis.
    const isV2   = version === 'v2';
    const isFake = data.verdict === 'FAKE' || data.is_deepfake === true;
    const mesoScore  = data.model_scores?.mesonet  ?? data.mesonet?.score  ?? 0.5;
    const xceptScore = data.model_scores?.xception ?? data.xceptionnet?.score ?? 0.5;
    const confidence = data.confidence ?? 0.5;
    
    // Calculate display confidence based on the verdict to provide intuitive UI feedback
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
        // Include legacy baseline models if the classic pipeline was utilized
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

  /**
   * Generates CSS utility classes for the result bar based on the suspiciousness level.
   * @param {number} score - Raw probability score of manipulation.
   */
  const getFakeBarColor = (score) =>
    score > 0.7 ? 'from-red-500 to-red-600'
    : score > 0.4 ? 'from-yellow-500 to-orange-500'
    : 'from-green-500 to-emerald-500';

  /**
   * Provides a human-readable interpretation of numerical inference scores.
   * @param {number} score - P(fake) from the model.
   */
  const getScoreInterpretation = (score) => {
    if (score < 0.1) return 'Very confident — no spatial or texture manipulation detected.';
    if (score < 0.3) return 'Low potential for manipulation — likely authentic source.';
    if (score < 0.6) return 'Moderate anomaly markers detected — use caution.';
    return 'Critical manipulation indicators identified within the region.';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 text-white">

      {/* Global Header */}
      <div className="bg-black/40 backdrop-blur-sm border-b border-white/10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">DeepTrust</h1>
            <p className="text-xs text-blue-300 mt-0.5">Explainable AI Deepfake Detection Suite</p>
          </div>
          <span className={`text-xs ${token ? 'text-green-400' : 'text-gray-500'}`}>
            {token ? '● System Authenticated' : '● Guest Mode'}
          </span>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">

        {/* Inference Pipeline Selector */}
        <div className="mb-6 flex justify-center">
          <div className="bg-black/30 rounded-2xl p-1 border border-white/10 flex gap-1">
            <button onClick={() => { setModelVersion('v2'); setResults(null); }}
              className={`px-6 py-3 rounded-xl font-semibold transition-all flex items-center gap-2 text-sm ${
                modelVersion === 'v2' ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg' : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}>
              <Brain className="w-4 h-4" />
              DeepTrust V2
              <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full font-normal">SOTA</span>
            </button>
            <button onClick={() => { setModelVersion('v1'); setResults(null); }}
              className={`px-6 py-3 rounded-xl font-semibold transition-all flex items-center gap-2 text-sm ${
                modelVersion === 'v1' ? 'bg-white/10 text-white border border-white/20' : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}>
              <FlaskConical className="w-4 h-4" />
              Classic Baseline
            </button>
          </div>
        </div>

        {/* Model Capability Information Panel */}
        <div className={`mb-6 p-3 rounded-xl border text-xs ${
          modelVersion === 'v2' ? 'bg-blue-900/20 border-blue-500/20 text-blue-300' : 'bg-gray-800/40 border-gray-600/20 text-gray-400'
        }`}>
          {modelVersion === 'v2'
            ? '🎯 Ensemble Configuration: MesoNet + XceptionNet specialized for FaceForensics++. Features Platt-calibration for probability estimation and Grad-CAM for spatial localization of artifacts.'
            : '🔬 Baseline Configuration: Traditional heuristic analyzers (FFT/DCT and Biological symmetry) used for academic comparison and sanity checking.'}
        </div>

        {/* Empty State / Ingestion Zone */}
        {!file && (
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold mb-3 bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
              Verify Automated Integrity
            </h2>
            <p className="text-blue-200 mb-8">Upload media for forensic-grade detection with explainable heatmaps</p>
            <div onClick={() => fileInputRef.current?.click()}
              className="max-w-2xl mx-auto border-2 border-dashed border-blue-500/40 rounded-2xl p-16 hover:border-blue-400 hover:bg-white/3 transition-all cursor-pointer group">
              <Upload className="w-14 h-14 mx-auto mb-4 text-blue-400 group-hover:scale-110 transition-transform" />
              <p className="text-lg mb-1 font-medium">Click to select media</p>
              <p className="text-sm text-blue-300/70">Images (JPG, PNG) or Videos (MP4, AVI) — Pre-cropped faces yield the highest precision</p>
              <input ref={fileInputRef} type="file" accept="image/*,video/*" onChange={handleFileSelect} className="hidden" />
            </div>
            {/* Feature Highlights */}
            <div className="grid md:grid-cols-4 gap-4 mt-10">
              {[
                { icon: Brain,     title: 'CNN Ensemble',     desc: 'Dual-architecture verification' },
                { icon: BarChart3, title: 'DFDC Verified',    desc: 'Validated on unseen frames' },
                { icon: Eye,       title: 'Visual Evidence',  desc: 'Grad-CAM XAI heatmaps' },
                { icon: Layers,    title: 'Precision Calibration', desc: 'Normalized probability' }
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

        {/* Primary Analysis Dashboard */}
        {file && (
          <div className="grid lg:grid-cols-2 gap-6">

            {/* Viewport: Media & Visualization */}
            <div className="bg-white/4 backdrop-blur-sm rounded-2xl p-5 border border-white/10">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-sm">Forensic Preview</h3>
                {/* Layer Control for explainable heatmaps */}
                {results?.gradcam && (
                  <div className="flex gap-1 bg-black/30 rounded-lg p-1 text-xs">
                    {['original', 'mesonet', 'xceptionnet'].map(v => (
                      <button key={v} onClick={() => setGradcamView(v)}
                        className={`px-2.5 py-1 rounded capitalize transition-all ${
                          gradcamView === v ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
                        }`}>
                        {v === 'xceptionnet' ? 'Xcept' : v === 'mesonet' ? 'Meso' : 'Raw'}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              {preview && (
                <div className="relative rounded-xl overflow-hidden">

                  {/* Dynamic Image & Heatmap Renderer */}
                  {file?.type.startsWith('image/') && (
                    <>
                      {(!results?.gradcam || gradcamView === 'original') && (
                        <img src={preview} alt="Input" className="w-full rounded-xl" />
                      )}

                      {results?.gradcam && gradcamView === 'mesonet' && (
                        <img
                          src={`data:image/jpeg;base64,${results.gradcam.mesonet.image_base64}`}
                          alt="MesoNet Anomaly Localization"
                          className="w-full rounded-xl"
                        />
                      )}

                      {results?.gradcam && gradcamView === 'xceptionnet' && (
                        <img
                          src={`data:image/jpeg;base64,${results.gradcam.xceptionnet.image_base64}`}
                          alt="XceptionNet Anomaly Localization"
                          className="w-full rounded-xl"
                        />
                      )}
                    </>
                  )}

                  {/* Standard Video Playback */}
                  {file?.type.startsWith('video/') && (
                    <video
                      src={preview}
                      controls
                      className="w-full rounded-xl"
                    />
                  )}

                  {/* Integrated Verdict Overlay */}
                  {results && !results.noFace && (
                    <div className={`absolute top-3 right-3 px-3 py-1.5 rounded-lg text-xs font-bold border backdrop-blur-sm ${
                      results.isDeepfake
                        ? 'bg-red-900/80 border-red-500/60 text-red-300'
                        : 'bg-green-900/80 border-green-500/60 text-green-300'
                    }`}>
                      {results.isDeepfake ? '⚠ MANIPULATED' : '✓ AUTHENTIC'}
                    </div>
                  )}

                  {/* Face Detection Warning */}
                  {results?.noFace && (
                    <div className="absolute top-3 right-3 px-3 py-1.5 rounded-lg text-xs font-bold border backdrop-blur-sm bg-yellow-900/80 border-yellow-500/60 text-yellow-300">
                      ⚠ DETECTION FAILURE
                    </div>
                  )}

                </div>
              )}

              {/* XAI Interpretation Guide */}
              {results?.gradcam && gradcamView !== 'original' && (
                <div className="mt-3 space-y-2">
                  <div className="flex items-center gap-3 text-xs text-gray-500">
                    <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-sm bg-blue-500 opacity-60"/><span>Scan Baseline</span></div>
                    <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-sm bg-yellow-400 opacity-60"/><span>Secondary Signal</span></div>
                    <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-sm bg-red-500 opacity-60"/><span>High Attention Area</span></div>
                  </div>
                  <p className="text-xs text-gray-400 leading-relaxed italic">
                    {results.isDeepfake
                      ? 'The model exhibits high neuronal activation (warm colors) in regions containing structural artifacts or texture inconsistencies.'
                      : 'Attention map indicates a standard focus on diagnostic facial regions with no significant anomaly markers found.'}
                  </p>
                </div>
              )}

              <div className="flex gap-3 mt-4">
                <button onClick={analyzeMedia} disabled={analyzing}
                  className="flex-1 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 px-6 py-3 rounded-xl font-semibold text-sm transition-all shadow-lg active:scale-95">
                  {analyzing ? 'Processing Inference...' : 'Begin Forensic Analysis'}
                </button>
                <button onClick={() => { setFile(null); setPreview(null); setResults(null); setError(null); }}
                  className="px-5 py-3 bg-white/8 hover:bg-white/15 rounded-xl text-sm transition-all">
                  Clear
                </button>
              </div>
              {error && <div className="mt-3 p-3 bg-red-900/30 border border-red-500/30 rounded-xl text-xs text-red-300">{error}</div>}
            </div>

            {/* Intelligence Panel: Quantitative Results */}
            <div className="bg-white/4 backdrop-blur-sm rounded-2xl p-5 border border-white/10 overflow-hidden">
              <h3 className="font-semibold mb-4 text-sm">Detection Intelligence</h3>

              {/* Inactive State Feedback */}
              {!results && !analyzing && (
                <div className="text-center py-16 text-gray-500 text-sm flex flex-col items-center gap-3">
                   <div className="w-12 h-12 rounded-full border-2 border-dashed border-gray-700 flex items-center justify-center">
                      <Brain className="w-6 h-6 opacity-20"/>
                   </div>
                   Ready for ingestion. Initiate analysis to begin.
                </div>
              )}

              {/* Active Processing Feedback */}
              {analyzing && (
                <div className="text-center py-16">
                  <div className="animate-spin rounded-full h-14 w-14 border-b-2 border-blue-500 mx-auto mb-4"/>
                  <p className="text-blue-300 text-sm font-medium">Running ensemble validation...</p>
                  <p className="text-xs text-gray-500 mt-1">Cross-referencing MesoNet & XceptionNet weights</p>
                </div>
              )}

              {/* Result Summary Presentation */}
              {results && (
                <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">

                  {/* Primary Verdict Card */}
                  {results.noFace ? (
                    <div className="p-4 rounded-xl border-2 bg-yellow-900/30 border-yellow-500/50">
                      <div className="flex items-start gap-3">
                        <AlertCircle className="w-7 h-7 text-yellow-400 flex-shrink-0 mt-0.5" />
                        <div>
                          <h4 className="text-lg font-bold text-yellow-400">UNRELIABLE RESULT</h4>
                          <p className="text-sm text-gray-300 mt-0.5">{results.explanation || 'No facial biometric detected.'}</p>
                          <p className="text-xs text-gray-500 mt-1">
                            The detection pipeline requires a clearly visible human face. Forensic baseline results may be inaccurate.
                          </p>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className={`p-4 rounded-xl border-2 transition-colors duration-500 ${
                      results.isDeepfake ? 'bg-red-900/30 border-red-500/50' : 'bg-green-900/30 border-green-500/50'
                    }`}>
                      <div className="flex items-start gap-3">
                        {results.isDeepfake
                          ? <ShieldAlert className="w-7 h-7 text-red-400 flex-shrink-0"/>
                          : <ShieldCheck className="w-7 h-7 text-green-400 flex-shrink-0"/>}
                        <div>
                          <h4 className={`text-lg font-bold ${results.isDeepfake ? 'text-red-400' : 'text-green-400'}`}>
                            {results.isDeepfake ? 'MANIPULATION DETECTED' : 'AUTHENTIC MEDIA'}
                          </h4>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-sm text-gray-300">Signal Confidence:</span>
                            <span className="text-sm font-bold text-white">{results.confidencePct}</span>
                            {results.calibrationActive && (
                              <span className="text-[10px] bg-blue-500/25 text-blue-300 px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wider">Calibrated</span>
                            )}
                          </div>
                        </div>
                      </div>
                      {/* Technical Constraints for Video Analysis */}
                      {results.isVideo && (
                        <div className="mt-3 p-3 bg-amber-900/20 border border-amber-500/30 rounded-lg">
                           <div className="flex items-center gap-1.5 text-amber-300 font-bold text-[10px] uppercase mb-1">
                              <Info className="w-3 h-3"/> Temporal Note
                           </div>
                          <p className="text-[11px] text-amber-200/70 leading-relaxed">
                            Video inference performed across {results.framesAnalyzed} temporal samples. 
                            Aggregated confidence reflects a cross-frame mean probability.
                          </p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Detailed Analysis Tabs */}
                  {!results.noFace && (
                    <>
                      <div className="flex gap-1 border-b border-white/10">
                        {['overview', 'model breakdown', 'XAI forensics'].map(tab => {
                           const key = tab === 'model breakdown' ? 'models' : tab === 'XAI forensics' ? 'xai' : 'overview';
                           return (
                              <button key={key} onClick={() => setActiveTab(key)}
                                className={`px-4 py-2 text-xs font-bold uppercase tracking-widest transition-colors ${
                                  activeTab === key ? 'text-blue-400 border-b-2 border-blue-400' : 'text-gray-500 hover:text-gray-300'
                                }`}>{tab}</button>
                           );
                        })}
                      </div>

                      {/* DATA PANEL: Overview Scoring */}
                      {activeTab === 'overview' && (
                        <div className="space-y-3 pt-2">
                          <div className="bg-black/20 rounded-xl p-4">
                            <div className="flex items-center gap-2 mb-4">
                              <h5 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Aggregation Metrics</h5>
                              <div className="group relative">
                                <Info className="w-3.5 h-3.5 text-gray-700 cursor-help"/>
                                <div className="hidden group-hover:block absolute left-0 top-5 z-10 bg-slate-800 border border-white/10 rounded-lg p-2 text-[10px] text-gray-300 w-56 shadow-2xl">
                                  Scores represent P(manipulation) where values {'>'}30% indicate detectable synthetic markers.
                                </div>
                              </div>
                            </div>

                            <div className="space-y-6">
                              {/* MesoNet Metric */}
                              <div>
                                <div className="flex justify-between items-end mb-1.5">
                                   <span className="text-[11px] font-bold text-gray-300 uppercase">MesoNet Architecture</span>
                                   <span className={`text-xs font-bold ${results.mesoFakeScore >= 0.3 ? 'text-red-400' : 'text-green-400'}`}>
                                      {results.mesoFakePct}% Anomaly
                                   </span>
                                </div>
                                <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                                  <div className={`h-full bg-gradient-to-r ${getFakeBarColor(results.mesoFakeScore)} transition-all duration-1000 ease-out`}
                                    style={{ width: `${results.mesoFakeScore * 100}%` }}/>
                                </div>
                              </div>

                              {/* XceptionNet Metric */}
                              <div>
                                <div className="flex justify-between items-end mb-1.5">
                                   <span className="text-[11px] font-bold text-gray-300 uppercase">XceptionNet Architecture</span>
                                   <span className={`text-xs font-bold ${results.xceptFakeScore >= 0.3 ? 'text-red-400' : 'text-green-400'}`}>
                                      {results.xceptFakePct}% Anomaly
                                   </span>
                                </div>
                                <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                                  <div className={`h-full bg-gradient-to-r ${getFakeBarColor(results.xceptFakeScore)} transition-all duration-1000 delay-100 ease-out`}
                                    style={{ width: `${results.xceptFakeScore * 100}%` }}/>
                                </div>
                              </div>

                              {/* Central Consensus */}
                              <div className="pt-4 border-t border-white/5">
                                <div className="flex justify-between items-center">
                                  <span className="text-xs font-bold text-gray-300">Ensemble Consensus</span>
                                  <span className={`text-sm font-black ${(results.ensembleScore ?? 0) >= 0.3 ? 'text-red-400' : 'text-green-400'}`}>
                                    {((results.ensembleScore ?? 0) * 100).toFixed(1)}% COMBINED P(FAKE)
                                  </span>
                                </div>
                                <p className="text-[10px] text-gray-600 mt-1 leading-relaxed">
                                  Weighted heuristic synthesis: {results.models.mesonet.weight*100}% Surface Analysis + {results.models.xception.weight*100}% Semantic Analysis.
                                </p>
                              </div>
                            </div>
                          </div>

                          {/* Training Metadata (V2 Only) */}
                          {results.modelVersion === 'v2' && (
                            <div className="bg-blue-900/10 border border-blue-500/10 rounded-xl p-3">
                               <p className="text-[10px] font-black text-blue-400/80 uppercase tracking-widest mb-2">Internal Validation Metrics (SOTA)</p>
                               <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[10px] text-blue-200/50">
                                  <div className="flex justify-between"><span>DFDC Target:</span> <span className="text-white">95.52%</span></div>
                                  <div className="flex justify-between"><span>AUC-ROC:</span> <span className="text-white">0.9927</span></div>
                                  <div className="flex justify-between"><span>Recall:</span> <span className="text-white">95.48%</span></div>
                                  <div className="flex justify-between"><span>Specificity:</span> <span className="text-white">95.56%</span></div>
                               </div>
                            </div>
                          )}
                        </div>
                      )}

                      {/* DATA PANEL: Model Details */}
                      {activeTab === 'models' && (
                        <div className="space-y-3 pt-2">
                          {Object.entries(results.models).map(([name, data]) => (
                            <div key={name} className="bg-black/20 rounded-xl p-4 border border-white/5">
                              <div className="flex justify-between items-start mb-3">
                                <div>
                                  <h5 className="font-bold text-[11px] text-white uppercase tracking-tighter">
                                    {name === 'xception' ? 'XceptionNet V2 Core' : name.toUpperCase()} 
                                  </h5>
                                  <p className="text-[10px] text-gray-500 font-medium">
                                     Configuration: {data.version} · Weight: {data.weight * 100}%
                                  </p>
                                </div>
                                <div className="text-right">
                                  <p className={`text-lg font-black tracking-tighter leading-none ${data.score >= 0.3 ? 'text-red-400' : 'text-green-400'}`}>
                                    {(data.score * 100).toFixed(1)}%
                                  </p>
                                  <span className={`text-[10px] font-black px-1.5 py-0.5 rounded mt-1.5 inline-block ${
                                    data.score >= 0.3 ? 'bg-red-500/10 text-red-400' : 'bg-green-500/10 text-green-400'
                                  }`}>{data.score >= 0.3 ? 'SUSPICIOUS' : 'STIMULUS NORMAL'}</span>
                                </div>
                              </div>
                              <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                                <div className={`h-full bg-gradient-to-r ${getFakeBarColor(data.score)}`} style={{ width: `${data.score * 100}%` }}/>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* DATA PANEL: XAI & Heatmaps */}
                      {activeTab === 'xai' && (
                        <div className="space-y-4 pt-2">
                          {results.explanation && (
                            <div className="bg-black/20 rounded-xl p-4 border-l-2 border-blue-500/50">
                              <h5 className="text-[10px] font-black uppercase text-gray-400 mb-2 flex items-center gap-1.5">
                                <Info className="w-3 h-3"/> AI Rationale Summary
                              </h5>
                              <p className="text-xs text-gray-300 leading-relaxed font-medium">{results.explanation}</p>
                            </div>
                          )}

                          {results.gradcam ? (
                            <div className="bg-black/20 rounded-xl p-4">
                              <h5 className="text-[10px] font-black uppercase text-gray-400 mb-3 tracking-widest">Grad-CAM Spatial Interrogation</h5>
                              <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                  <div className="aspect-square rounded-lg border border-white/5 overflow-hidden">
                                     <img src={`data:image/jpeg;base64,${results.gradcam.mesonet.image_base64}`} alt="MesoNet Activation" className="w-full h-full object-cover"/>
                                  </div>
                                  <div className="text-center">
                                    <p className="text-[10px] font-bold text-gray-300 uppercase">Architecture: MesoNet</p>
                                    <p className="text-[9px] text-gray-600 uppercase">Lower-layer texture scrutiny</p>
                                  </div>
                                </div>
                                <div className="space-y-2">
                                  <div className="aspect-square rounded-lg border border-white/5 overflow-hidden">
                                     <img src={`data:image/jpeg;base64,${results.gradcam.xceptionnet.image_base64}`} alt="XceptionNet Activation" className="w-full h-full object-cover"/>
                                  </div>
                                  <div className="text-center">
                                    <p className="text-[10px] font-bold text-gray-300 uppercase">Architecture: XceptionNet</p>
                                    <p className="text-[9px] text-gray-600 uppercase">High-layer structural scrutiny</p>
                                  </div>
                                </div>
                              </div>
                            </div>
                          ) : (
                            <div className="bg-black/20 rounded-xl p-12 text-center text-gray-600 text-xs font-bold uppercase tracking-widest border border-dashed border-white/5">
                               Visual explanations unavailable for {results.modelVersion === 'v1' ? 'Classic Baseline' : 'selected configuration'}.
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