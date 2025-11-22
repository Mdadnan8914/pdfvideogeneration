import React, { useState, useEffect } from 'react';
import { getJobStatus, generateSummaryVideo, downloadSummaryVideo } from '../services/api';
import './SummaryVideoPrompt.css';

const SummaryVideoPrompt = ({ jobId, onVideoGenerated, onDismiss }) => {
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [videoStatus, setVideoStatus] = useState(null);

  useEffect(() => {
    // Check if summary video already exists
    const checkVideo = async () => {
      try {
        const response = await getJobStatus(jobId);
        if (response.metadata?.summary_video_path) {
          setVideoStatus('completed');
          if (onVideoGenerated) {
            onVideoGenerated(response);
          }
        }
      } catch (err) {
        console.error('Error checking summary video:', err);
      }
    };

    checkVideo();
  }, [jobId, onVideoGenerated]);

  const handleGenerateVideo = async () => {
    setGenerating(true);
    setError(null);

    try {
      await generateSummaryVideo(jobId);
      
      // Poll for video completion
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await getJobStatus(jobId);
          if (statusResponse.metadata?.summary_video_path) {
            clearInterval(pollInterval);
            setVideoStatus('completed');
            setGenerating(false);
            if (onVideoGenerated) {
              onVideoGenerated(statusResponse);
            }
          } else if (statusResponse.status === 'failed') {
            clearInterval(pollInterval);
            setError('Summary video generation failed');
            setGenerating(false);
          }
        } catch (err) {
          console.error('Error polling video status:', err);
        }
      }, 5000); // Poll every 5 seconds

      // Stop polling after 10 minutes
      setTimeout(() => {
        clearInterval(pollInterval);
        if (videoStatus !== 'completed') {
          setError('Video generation is taking longer than expected. Please check back later.');
          setGenerating(false);
        }
      }, 600000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start video generation');
      setGenerating(false);
    }
  };

  const handleDownloadVideo = async () => {
    try {
      const blob = await downloadSummaryVideo(jobId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `summary_video_${jobId}.mp4`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to download summary video');
    }
  };

  if (videoStatus === 'completed') {
    return (
      <div className="card summary-video-prompt">
        <h3>✓ Summary Video Generated!</h3>
        <p>The summary video has been generated successfully.</p>
        <div className="button-group">
          <button className="btn btn-success" onClick={handleDownloadVideo}>
            Download Summary Video
          </button>
          <button className="btn-secondary" onClick={onDismiss}>
            Close
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="card summary-video-prompt">
      <h3>Generate Summary Video?</h3>
      <p>
        Would you like to generate a video from the book summary?
        This will create a narrated video using the generated summary text.
      </p>
      
      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}

      {generating && (
        <div className="generating-section">
          <div className="loading-spinner"></div>
          <p>Generating summary video... This may take several minutes.</p>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: '100%' }}></div>
          </div>
        </div>
      )}

      <div className="button-group">
        <button
          className="btn btn-success"
          onClick={handleGenerateVideo}
          disabled={generating}
        >
          {generating ? 'Generating...' : 'Yes, Generate Summary Video'}
        </button>
        <button
          className="btn-secondary"
          onClick={onDismiss}
          disabled={generating}
        >
          No, Skip
        </button>
      </div>
    </div>
  );
};

export default SummaryVideoPrompt;

