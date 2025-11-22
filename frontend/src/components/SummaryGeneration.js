import React, { useState, useRef } from 'react';
import { summarizePDF, getJobStatus, downloadSummary } from '../services/api';
import './SummaryGeneration.css';

const SummaryGeneration = ({ onSummaryGenerated, onBack }) => {
  const [file, setFile] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);
  const statusIntervalRef = useRef(null);

  const handleFileSelect = (selectedFile) => {
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
      setError(null);
    } else {
      setError('Please select a valid PDF file');
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    handleFileSelect(droppedFile);
  };

  const handleFileInputChange = (e) => {
    const selectedFile = e.target.files[0];
    handleFileSelect(selectedFile);
  };

  const pollStatus = async (id) => {
    try {
      const jobStatus = await getJobStatus(id);
      setStatus(jobStatus);
      
      if (jobStatus.status === 'completed') {
        setIsGenerating(false);
        if (statusIntervalRef.current) {
          clearInterval(statusIntervalRef.current);
          statusIntervalRef.current = null;
        }
        // Fetch the summary text from the file
        if (jobStatus.metadata?.summary_path) {
          downloadSummary(id)
            .then(text => {
              onSummaryGenerated({
                ...jobStatus,
                metadata: {
                  ...jobStatus.metadata,
                  summary_text: text
                }
              });
            })
            .catch(err => {
              console.error('Error fetching summary text:', err);
              onSummaryGenerated(jobStatus);
            });
        } else {
          onSummaryGenerated(jobStatus);
        }
      } else if (jobStatus.status === 'failed') {
        setIsGenerating(false);
        setError(jobStatus.message || 'Summary generation failed');
        if (statusIntervalRef.current) {
          clearInterval(statusIntervalRef.current);
          statusIntervalRef.current = null;
        }
      }
    } catch (err) {
      console.error('Error polling status:', err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!file) {
      setError('Please select a PDF file');
      return;
    }

    setIsGenerating(true);
    setError(null);

    try {
      const response = await summarizePDF(file);
      setJobId(response.job_id);
      setStatus(response);
      
      // Start polling for status
      statusIntervalRef.current = setInterval(() => {
        pollStatus(response.job_id);
      }, 2000);
      
      // Poll immediately
      pollStatus(response.job_id);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start summarization. Please try again.');
      console.error('Summarization error:', err);
      setIsGenerating(false);
    }
  };

  React.useEffect(() => {
    return () => {
      if (statusIntervalRef.current) {
        clearInterval(statusIntervalRef.current);
      }
    };
  }, []);

  return (
    <div className="card summary-generation">
      <div className="card-header">
        <h2>Create Summary Video</h2>
        <p className="subtitle">Step 1: Generate Summary</p>
      </div>
      
      {!jobId ? (
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Upload PDF File</label>
            <div
              className={`file-input-wrapper ${isDragging ? 'dragover' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                onChange={handleFileInputChange}
                disabled={isGenerating}
              />
              <div className="file-input-label">
                {file ? (
                  <div>
                    <p>✓ {file.name}</p>
                    <p className="file-size">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                  </div>
                ) : (
                  <div>
                    <p>📄 Drag and drop your PDF here</p>
                    <p>or click to browse</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {error && (
            <div className="alert alert-error">
              {error}
            </div>
          )}

          <div className="button-group">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onBack}
              disabled={isGenerating}
            >
              Back
            </button>
            <button
              type="submit"
              className="btn"
              disabled={isGenerating || !file}
            >
              {isGenerating ? 'Generating Summary...' : 'Generate Summary'}
            </button>
          </div>
        </form>
      ) : (
        <div className="status-container">
          <div className="status-info">
            <h3>Generating Summary</h3>
            <p className="status-message">{status?.message || 'Processing...'}</p>
            {status?.progress !== null && status?.progress !== undefined && (
              <div className="progress-bar-container">
                <div 
                  className="progress-bar" 
                  style={{ width: `${status.progress}%` }}
                ></div>
                <span className="progress-text">{status.progress}%</span>
              </div>
            )}
          </div>
          
          {status?.metadata?.summary_stats && (
            <div className="summary-stats">
              <p><strong>Word Count:</strong> {status.metadata.summary_stats.word_count?.toLocaleString()}</p>
              <p><strong>Estimated Narration:</strong> ~{status.metadata.summary_stats.estimated_minutes?.toFixed(1)} minutes</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SummaryGeneration;

