import React, { useState } from 'react';
import './App.css';
import PDFUpload from './components/PDFUpload';
import JobStatus from './components/JobStatus';
import SummaryPrompt from './components/SummaryPrompt';
import SummaryVideoPrompt from './components/SummaryVideoPrompt';

function App() {
  const [currentJobId, setCurrentJobId] = useState(null);
  const [showSummaryPrompt, setShowSummaryPrompt] = useState(false);
  const [showSummaryVideoPrompt, setShowSummaryVideoPrompt] = useState(false);
  const [jobStatus, setJobStatus] = useState(null);
  const [summaryPromptShown, setSummaryPromptShown] = useState(false);
  const [summaryVideoPromptShown, setSummaryVideoPromptShown] = useState(false);

  const handleUploadSuccess = (jobId) => {
    setCurrentJobId(jobId);
    setShowSummaryPrompt(false);
    setShowSummaryVideoPrompt(false);
    setSummaryPromptShown(false);
    setSummaryVideoPromptShown(false);
    setJobStatus(null);
  };

  const handleMainVideoComplete = (status) => {
    setJobStatus(status);
    // Show summary prompt when main video is completed and has video path
    if (status?.status?.toLowerCase() === 'completed' && status?.metadata?.final_video_path) {
      // Only show if we haven't shown it yet and summary hasn't been generated
      if (!summaryPromptShown && !status?.metadata?.summary_path) {
        setShowSummaryPrompt(true);
        setSummaryPromptShown(true);
      }
    }
  };

  const handleSummaryGenerated = (status) => {
    setJobStatus(status);
    // Show summary video prompt when summary is completed
    if (status?.metadata?.summary_path) {
      // Only show if we haven't shown it yet and summary video hasn't been generated
      if (!summaryVideoPromptShown && !status?.metadata?.summary_video_path) {
        setShowSummaryVideoPrompt(true);
        setSummaryVideoPromptShown(true);
      }
    }
  };

  const handleSummaryVideoComplete = (status) => {
    setJobStatus(status);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>📚 PDF to Video Generator</h1>
        <p>Convert your PDF books into narrated videos</p>
      </header>

      <main className="App-main">
        {!currentJobId ? (
          <PDFUpload onUploadSuccess={handleUploadSuccess} />
        ) : (
          <>
            <JobStatus
              jobId={currentJobId}
              onStatusUpdate={handleMainVideoComplete}
            />
            
            {showSummaryPrompt && (
              <SummaryPrompt
                jobId={currentJobId}
                onSummaryGenerated={handleSummaryGenerated}
                onDismiss={() => setShowSummaryPrompt(false)}
              />
            )}

            {showSummaryVideoPrompt && jobStatus?.metadata?.summary_path && (
              <SummaryVideoPrompt
                jobId={currentJobId}
                onVideoGenerated={handleSummaryVideoComplete}
                onDismiss={() => setShowSummaryVideoPrompt(false)}
              />
            )}

            <button
              className="btn-secondary"
              onClick={() => {
                setCurrentJobId(null);
                setShowSummaryPrompt(false);
                setShowSummaryVideoPrompt(false);
                setJobStatus(null);
                setSummaryPromptShown(false);
                setSummaryVideoPromptShown(false);
              }}
            >
              Start New Job
            </button>
          </>
        )}
      </main>
    </div>
  );
}

export default App;

