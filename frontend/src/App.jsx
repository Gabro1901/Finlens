import { useState, useEffect, useRef } from 'react';
import PrintView from './components/PrintView';
import DesktopApp from './components/DesktopApp';
import MobileApp from './components/MobileApp';
import { useIsMobile } from './hooks/useIsMobile';
import './index.css';

function App() {
  const isPrintMode = new URLSearchParams(window.location.search).get('print') === 'true';
  const isMobile = useIsMobile(768);

  if (isPrintMode) {
    return <PrintView />;
  }

  // ── Core state (preserved exactly from original) ──
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  // Report is composed from two streaming documents:
  //   valuationMarkdown (top) + arbiterMarkdown (bottom)
  const [arbiterMarkdown, setArbiterMarkdown] = useState('');
  const [valuationMarkdown, setValuationMarkdown] = useState('');
  const [valuationStreaming, setValuationStreaming] = useState(false);
  const reportMarkdown = (() => {
    if (valuationMarkdown && arbiterMarkdown) {
      return `${valuationMarkdown}\n\n---\n\n${arbiterMarkdown}`;
    }
    return valuationMarkdown || arbiterMarkdown;
  })();
  const [currentStage, setCurrentStage] = useState('');
  const [currentMessage, setCurrentMessage] = useState('');
  const [targetTicker, setTargetTicker] = useState('');
  const [rawContextData, setRawContextData] = useState(null);
  const rawContextDataRef = useRef(null);
  const [valuationResultsData, setValuationResultsData] = useState(null);
  const valuationResultsDataRef = useRef(null);
  const wakeLockRef = useRef(null);
  const abortControllerRef = useRef(null);

  // ── Wake Lock helpers ──
  const requestWakeLock = async () => {
    try {
      if ('wakeLock' in navigator) {
        wakeLockRef.current = await navigator.wakeLock.request('screen');
      }
    } catch (err) {
      console.warn('Wake Lock error:', err);
    }
  };

  const releaseWakeLock = async () => {
    if (wakeLockRef.current !== null) {
      try {
        await wakeLockRef.current.release();
        wakeLockRef.current = null;
      } catch (err) {
        console.warn('Wake Lock release error:', err);
      }
    }
  };

  // ── UI state (new layout) ──
  const [activeView, setActiveView] = useState('report');    // 'report' | 'raw' | 'chat'
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [historyList, setHistoryList] = useState([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);

  const [apiKeys, setApiKeys] = useState(() => {
    const saved = localStorage.getItem('finlens_api_keys');
    if (saved) {
      try { return JSON.parse(saved); } catch (e) {}
    }
    return { openai: '', fred: '', congress: '', sec_email: '' };
  });

  useEffect(() => {
    localStorage.setItem('finlens_api_keys', JSON.stringify(apiKeys));
  }, [apiKeys]);

  const [language, setLanguage] = useState(() => {
    return localStorage.getItem('finlens_language') || 'en';
  });

  useEffect(() => {
    localStorage.setItem('finlens_language', language);
  }, [language]);

  // ── History management (preserved exactly) ──
  const fetchHistoryList = async () => {
    setIsHistoryLoading(true);
    try {
      const res = await fetch(`/api/history/`);
      if (res.ok) {
        const data = await res.json();
        setHistoryList(data);
      }
    } catch (e) {
      console.error("Failed to fetch history", e);
    } finally {
      setIsHistoryLoading(false);
    }
  };

  useEffect(() => {
    fetchHistoryList();
  }, []);

  const saveReportToHistory = async (tickerToSave, markdownToSave, rawDataToSave, valuationResultsToSave) => {
    try {
      const res = await fetch(`/api/history/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          ticker: tickerToSave, 
          markdown: markdownToSave,
          raw_data: rawDataToSave,
          valuation_results: valuationResultsToSave
        })
      });
      if (res.ok) {
        fetchHistoryList();
      }
    } catch (e) {
      console.error("Failed to save history", e);
    }
  };

  const handleSelectHistory = async (id) => {
    setIsHistoryOpen(false);
    try {
      const res = await fetch(`/api/history/${id}`);
      if (res.ok) {
        const data = await res.json();
        setTargetTicker(data.ticker);
        setArbiterMarkdown(data.markdown);
        setValuationMarkdown('');
        setValuationStreaming(false);
        setRawContextData(data.raw_data || null);
        rawContextDataRef.current = data.raw_data || null;
        setValuationResultsData(data.valuation_results || null);
        valuationResultsDataRef.current = data.valuation_results || null;
        setCurrentStage('complete');
        setActiveView('report');
      }
    } catch (e) {
      console.error("Failed to fetch report", e);
    }
  };

  const handleDeleteHistory = async (id, e) => {
    e.stopPropagation();
    try {
      const res = await fetch(`/api/history/${id}`, { method: 'DELETE' });
      if (res.ok) {
        fetchHistoryList();
      }
    } catch (err) {
      console.error(err);
    }
  };

  // ── SSE analysis pipeline (preserved exactly) ──
  const handleStartAnalysis = async (ticker) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    setIsAnalyzing(true);
    setArbiterMarkdown('');
    setValuationMarkdown('');
    setValuationStreaming(false);
    setRawContextData(null);
    rawContextDataRef.current = null;
    setValuationResultsData(null);
    valuationResultsDataRef.current = null;
    setCurrentStage('init');
    setCurrentMessage('');
    setTargetTicker(ticker);
    setActiveView('report');
    setIsChatOpen(false);
    await requestWakeLock();

    try {
      const response = await fetch(`/api/analysis/`, {
        method: 'POST',
        signal: abortController.signal,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          ticker, 
          llm_provider: 'openai', 
          llm_api_key: apiKeys.openai,
          fred_api_key: apiKeys.fred,
          congress_api_key: apiKeys.congress,
          sec_email: apiKeys.sec_email,
          language
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to start analysis: ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');

      let currentArbiter = '';
      let currentValuation = '';
      let buffer = '';
      let currentEvent = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.substring(7).trim();
          } else if (line.startsWith('data: ')) {
            const dataStr = line.substring(6).trim();
            if (!dataStr) continue;
            
            try {
              const data = JSON.parse(dataStr);
              if (currentEvent === 'status') {
                setCurrentStage(data.stage);
                setCurrentMessage(data.message || '');
              } else if (currentEvent === 'raw_data') {
                setRawContextData(data);
                rawContextDataRef.current = data;
              } else if (currentEvent === 'report_chunk') {
                currentArbiter += data.text;
                setArbiterMarkdown(currentArbiter);
              } else if (currentEvent === 'valuation_progress') {
                // Drive the overlay during model selection & computation
                setCurrentStage('valuation');
                setCurrentMessage(data.message || '');
                if (data.stage === 'model_selected') {
                  setCurrentMessage(`Valuation: ${data.model?.toUpperCase()} selected (${data.business_type || ''})`);
                }
              } else if (currentEvent === 'valuation_chunk') {
                // First chunk: valuation report is now the primary view — jump to top
                if (!valuationStreaming && !currentValuation) {
                  setValuationStreaming(true);
                  const mainEl = document.querySelector('main');
                  if (mainEl) mainEl.scrollTo({ top: 0, behavior: 'smooth' });
                  else window.scrollTo({ top: 0, behavior: 'smooth' });
                }
                currentValuation += data.text;
                setValuationMarkdown(currentValuation);
                // Keep overlay hidden while report streams (valuationStreaming stays true)
                setCurrentStage('valuation');
              } else if (currentEvent === 'valuation_results') {
                setValuationResultsData(data);
                valuationResultsDataRef.current = data;
              } else if (currentEvent === 'valuation_error') {
                console.error('Valuation error:', data.message || data);
                setCurrentMessage(`Valuation skipped: ${data.message || 'unknown error'}`);
              } else if (currentEvent === 'complete') {
                setCurrentStage('complete');
                setIsAnalyzing(false);
                const finalDoc = currentValuation
                  ? `${currentValuation}\n\n---\n\n${currentArbiter}`
                  : currentArbiter;
                saveReportToHistory(ticker, finalDoc, rawContextDataRef.current, valuationResultsDataRef.current);
                await releaseWakeLock();
              } else if (currentEvent === 'error') {
                setCurrentStage('error');
                setIsAnalyzing(false);
                console.error('Pipeline error:', data.message || data);
                await releaseWakeLock();
              }
            } catch (e) {
              console.error("Failed to parse SSE data", e, dataStr);
            }
          }
        }
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        console.log('Analysis aborted');
        setCurrentStage('cancelled');
        setIsAnalyzing(false);
        await releaseWakeLock();
        return;
      }
      console.error(err);
      setCurrentStage('error');
      setIsAnalyzing(false);
      await releaseWakeLock();
    }
  };

  const handleStopAnalysis = async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    
    // Mark whichever document is active as cancelled
    if (!arbiterMarkdown && !valuationMarkdown) {
      setArbiterMarkdown("# Analysis Cancelled\n\nGeneration was stopped before completion.");
    } else if (valuationStreaming) {
      setValuationMarkdown((v) => v + "\n\n> **Analysis Cancelled**");
    } else {
      setArbiterMarkdown((a) => a + "\n\n> **Analysis Cancelled**");
    }
    setIsAnalyzing(false);
    setCurrentStage('cancelled');
    await releaseWakeLock();
  };

  // ── Navigation handler ──
  const handleClearAnalysis = () => {
    setArbiterMarkdown('');
    setValuationMarkdown('');
    setValuationStreaming(false);
    setTargetTicker('');
    setRawContextData(null);
    setValuationResultsData(null);
    setCurrentStage('');
  };

  const sharedProps = {
    isAnalyzing,
    reportMarkdown,
    currentStage,
    currentMessage,
    valuationStreaming,
    targetTicker,
    rawContextData,
    valuationResultsData,
    activeView,
    setActiveView,
    isSettingsOpen,
    setIsSettingsOpen,
    isChatOpen,
    setIsChatOpen,
    isHistoryOpen,
    setIsHistoryOpen,
    historyList,
    isHistoryLoading,
    apiKeys,
    setApiKeys,
    language,
    setLanguage,
    handleStartAnalysis,
    handleStopAnalysis,
    handleClearAnalysis,
    handleSelectHistory,
    handleDeleteHistory
  };

  return isMobile ? <MobileApp {...sharedProps} /> : <DesktopApp {...sharedProps} />;
}

export default App;
