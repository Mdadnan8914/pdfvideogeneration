import React, { useState, useEffect } from 'react';
import { listCartesiaVoices, listCartesiaModels, getCartesiaVoice } from '../services/api';
import './CartesiaConfig.css';

const CartesiaConfig = ({ voiceId, modelId, onVoiceChange, onModelChange, disabled = false }) => {
  const [voices, setVoices] = useState([]);
  const [models, setModels] = useState([]);
  const [selectedVoice, setSelectedVoice] = useState(voiceId || '');
  const [selectedModel, setSelectedModel] = useState(modelId || 'sonic-3');
  const [voiceDetails, setVoiceDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadCartesiaData();
  }, []);

  useEffect(() => {
    if (selectedVoice) {
      loadVoiceDetails(selectedVoice);
    } else {
      setVoiceDetails(null);
    }
  }, [selectedVoice]);

  useEffect(() => {
    if (onVoiceChange) {
      onVoiceChange(selectedVoice);
    }
  }, [selectedVoice, onVoiceChange]);

  useEffect(() => {
    if (onModelChange) {
      onModelChange(selectedModel);
    }
  }, [selectedModel, onModelChange]);

  const loadCartesiaData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [voicesResponse, modelsResponse] = await Promise.all([
        listCartesiaVoices('en'), // Filter for English voices by default
        listCartesiaModels()
      ]);
      setVoices(voicesResponse.voices || []);
      setModels(modelsResponse.models || []);
      
      // Set default voice if none selected
      if (!selectedVoice && voicesResponse.voices && voicesResponse.voices.length > 0) {
        const defaultVoice = voicesResponse.voices.find(v => v.id === '98a34ef2-2140-4c28-9c71-663dc4dd7022') 
          || voicesResponse.voices[0];
        setSelectedVoice(defaultVoice.id);
      }
    } catch (err) {
      console.error('Error loading Cartesia data:', err);
      setError('Failed to load Cartesia voices and models. Using defaults.');
      // Set fallback defaults
      setVoices([
        {
          id: '98a34ef2-2140-4c28-9c71-663dc4dd7022',
          name: 'Tessa',
          language: 'en',
          tags: ['Emotive', 'Expressive'],
          description: 'Expressive American English voice'
        }
      ]);
      setModels([
        { id: 'sonic-3', name: 'Sonic 3', description: 'Latest streaming TTS model' }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const loadVoiceDetails = async (voiceIdToLoad) => {
    try {
      const details = await getCartesiaVoice(voiceIdToLoad);
      setVoiceDetails(details);
    } catch (err) {
      console.error('Error loading voice details:', err);
      // Find voice in local list as fallback
      const voice = voices.find(v => v.id === voiceIdToLoad);
      if (voice) {
        setVoiceDetails(voice);
      }
    }
  };

  const handleVoiceChange = (e) => {
    setSelectedVoice(e.target.value);
  };

  const handleModelChange = (e) => {
    setSelectedModel(e.target.value);
  };

  if (loading) {
    return (
      <div className="cartesia-config">
        <div className="loading">Loading Cartesia configuration...</div>
      </div>
    );
  }

  return (
    <div className="cartesia-config">
      {error && (
        <div className="alert alert-warning">
          {error}
        </div>
      )}

      <div className="form-group">
        <label htmlFor="cartesiaModel">Model</label>
        <select
          id="cartesiaModel"
          value={selectedModel}
          onChange={handleModelChange}
          disabled={disabled}
        >
          {models.map((model) => (
            <option key={model.id} value={model.id}>
              {model.name || model.id}
            </option>
          ))}
        </select>
        {models.find(m => m.id === selectedModel)?.description && (
          <small className="form-help">
            {models.find(m => m.id === selectedModel).description}
          </small>
        )}
      </div>

      <div className="form-group">
        <label htmlFor="cartesiaVoice">Voice</label>
        <select
          id="cartesiaVoice"
          value={selectedVoice}
          onChange={handleVoiceChange}
          disabled={disabled}
        >
          <option value="">Select a voice...</option>
          {voices.map((voice) => (
            <option key={voice.id} value={voice.id}>
              {voice.name || voice.id} {voice.tags && voice.tags.length > 0 && `(${voice.tags.join(', ')})`}
            </option>
          ))}
        </select>
        {voiceDetails && (
          <div className="voice-details">
            {voiceDetails.description && (
              <p className="voice-description">{voiceDetails.description}</p>
            )}
            {voiceDetails.tags && voiceDetails.tags.length > 0 && (
              <div className="voice-tags">
                {voiceDetails.tags.map((tag, idx) => (
                  <span key={idx} className="tag">{tag}</span>
                ))}
              </div>
            )}
            {voiceDetails.language && (
              <small className="voice-language">Language: {voiceDetails.language}</small>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default CartesiaConfig;

