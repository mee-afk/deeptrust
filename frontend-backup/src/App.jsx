import axios from 'axios';
import { useState } from 'react';
import './App.css';

function App() {
  const [token, setToken] = useState('');
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState(null);

  // Login
  const handleLogin = async () => {
    try {
      const formData = new URLSearchParams();
      formData.append('username', 'jane@test.com');
      formData.append('password', 'TestPass123');
      
      const response = await axios.post('http://localhost:8001/token', formData);
      setToken(response.data.access_token);
      alert('✅ Logged in successfully!');
    } catch (error) {
      alert('❌ Login failed: ' + error.message);
    }
  };

  // Handle file selection
  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    setFile(selectedFile);
    
    // Create preview
    const reader = new FileReader();
    reader.onloadend = () => {
      setPreview(reader.result);
    };
    reader.readAsDataURL(selectedFile);
  };

  // Upload and analyze
  const handleAnalyze = async () => {
    if (!file) {
      alert('Please select an image first');
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      // Upload to analysis service
      const uploadData = new FormData();
      uploadData.append('file', file);

      const uploadResponse = await axios.post(
        'http://localhost:8002/upload/',
        uploadData,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      console.log('Upload response:', uploadResponse.data);

      // Run ML prediction
      const predictData = new FormData();
      predictData.append('file', file);

      const predictResponse = await axios.post(
        'http://localhost:8003/predict',
        predictData
      );

      setResult(predictResponse.data);
    } catch (error) {
      alert('❌ Analysis failed: ' + error.message);
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🔍 DeepTrust - Deepfake Detector</h1>
        
        {/* Login Section */}
        {!token && (
          <div className="section">
            <button onClick={handleLogin} className="btn-primary">
              Login (Demo Account)
            </button>
          </div>
        )}

        {/* Upload Section */}
        {token && (
          <div className="section">
            <h2>Upload Image for Analysis</h2>
            
            <input 
              type="file" 
              accept="image/*" 
              onChange={handleFileChange}
              className="file-input"
            />

            {preview && (
              <div className="preview">
                <h3>Preview:</h3>
                <img src={preview} alt="Preview" style={{maxWidth: '400px'}} />
              </div>
            )}

            <button 
              onClick={handleAnalyze} 
              disabled={!file || loading}
              className="btn-primary"
            >
              {loading ? '🔄 Analyzing...' : '🚀 Analyze Image'}
            </button>
          </div>
        )}

        {/* Results Section */}
        {result && (
          <div className="results">
            <h2>Analysis Results</h2>
            
            <div className={`verdict ${result.is_deepfake ? 'fake' : 'real'}`}>
              <h3>
                {result.is_deepfake ? '⚠️ DEEPFAKE DETECTED' : '✅ AUTHENTIC'}
              </h3>
              <p>Confidence: {(result.confidence_score * 100).toFixed(1)}%</p>
            </div>

            <div className="model-scores">
              <h3>Individual Model Scores:</h3>
              
              <div className="score-card">
                <span>MesoNet:</span>
                <div className="score-bar">
                  <div 
                    className="score-fill" 
                    style={{width: `${result.model_scores.mesonet * 100}%`}}
                  />
                </div>
                <span>{(result.model_scores.mesonet * 100).toFixed(1)}%</span>
              </div>

              <div className="score-card">
                <span>XceptionNet:</span>
                <div className="score-bar">
                  <div 
                    className="score-fill" 
                    style={{width: `${result.model_scores.xception * 100}%`}}
                  />
                </div>
                <span>{(result.model_scores.xception * 100).toFixed(1)}%</span>
              </div>

              <div className="score-card">
                <span>Frequency Analysis:</span>
                <div className="score-bar">
                  <div 
                    className="score-fill" 
                    style={{width: `${result.model_scores.frequency * 100}%`}}
                  />
                </div>
                <span>{(result.model_scores.frequency * 100).toFixed(1)}%</span>
              </div>

              <div className="score-card">
                <span>Biological Analysis:</span>
                <div className="score-bar">
                  <div 
                    className="score-fill" 
                    style={{width: `${result.model_scores.biological * 100}%`}}
                  />
                </div>
                <span>{(result.model_scores.biological * 100).toFixed(1)}%</span>
              </div>
            </div>

            <div className="voting">
              <h3>Ensemble Voting:</h3>
              <p>Fake votes: {result.voting.fake_votes} | Real votes: {result.voting.real_votes}</p>
              <p>Final Score: {(result.ensemble_score * 100).toFixed(1)}%</p>
            </div>
          </div>
        )}
      </header>
    </div>
  );
}

export default App;