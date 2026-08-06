import { useState, useEffect, useRef } from 'react';
import { Search, Loader2, FileDown, Download, Zap } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useDebounce } from '../hooks/useDebounce';

export default function CommandBar({ 
  onStartAnalysis, 
  onStopAnalysis,
  isAnalyzing, 
  currentStage,
  currentMessage,
  reportMarkdown, 
  ticker: activeTicker,
  activeView,
  onViewChange,
  hasRawData,
  hasValuationResults
}) {
  const [ticker, setTicker] = useState('');
  const [isExporting, setIsExporting] = useState(false);
  
  const [suggestions, setSuggestions] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const dropdownRef = useRef(null);

  const debouncedTicker = useDebounce(ticker, 300);

  useEffect(() => {
    if (debouncedTicker.trim().length >= 1) {
      const fetchSuggestions = async () => {
        setIsSearching(true);
        try {
          const res = await fetch(`/api/search/?q=${encodeURIComponent(debouncedTicker)}`);
          if (res.ok) {
            const data = await res.json();
            setSuggestions(data.results || []);
            setShowSuggestions(true);
          }
        } catch (e) {
          console.error("Failed to fetch suggestions");
        } finally {
          setIsSearching(false);
        }
      };
      fetchSuggestions();
    } else {
      setSuggestions([]);
      setShowSuggestions(false);
    }
  }, [debouncedTicker]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (ticker.trim() && !isAnalyzing) {
      setShowSuggestions(false);
      onStartAnalysis(ticker.trim());
    }
  };

  const handleSuggestionClick = (symbol) => {
    setTicker(symbol);
    setShowSuggestions(false);
    if (!isAnalyzing) {
      onStartAnalysis(symbol);
    }
  };

  const handleExportPdf = async () => {
    setIsExporting(true);
    try {
      const response = await fetch(`/api/export/pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ markdown_content: reportMarkdown, ticker: activeTicker || 'Report' })
      });
      
      if (!response.ok) throw new Error('Export failed');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `FinLens_${activeTicker || 'Report'}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (e) {
      console.error(e);
      alert('PDF generation failed. Please check the backend console.');
    } finally {
      setIsExporting(false);
    }
  };

  const handleExportMarkdown = async () => {
    setIsExporting(true);
    try {
      const response = await fetch(`/api/export/markdown`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ markdown_content: reportMarkdown, ticker: activeTicker || 'Report' })
      });
      
      if (!response.ok) throw new Error('Export failed');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `FinLens_${activeTicker || 'Report'}.md`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (e) {
      console.error(e);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div 
      className="commandbar-bg w-full z-40 flex items-center gap-4 px-4 border-b border-zinc-800/60"
      style={{ minHeight: 'var(--commandbar-height)' }}
    >
      {/* Ticker search */}
      <form onSubmit={handleSubmit} className="flex items-center gap-2.5 w-[400px]">
        <div className="relative flex-1 glow-focus rounded-lg transition-all duration-200">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            {isAnalyzing ? (
              <Loader2 className="h-4 w-4 text-theme-accent animate-spin" />
            ) : (
              <Search className="h-4 w-4 text-zinc-400" />
            )}
          </div>
          <input
            type="text"
            value={ticker}
            onChange={(e) => {
              setTicker(e.target.value.toUpperCase());
              setShowSuggestions(true);
            }}
            onFocus={() => {
              if (suggestions.length > 0) setShowSuggestions(true);
            }}
            placeholder="Search company or ticker..."
            className="block w-full pl-9 pr-3 py-2 bg-zinc-900/60 border border-zinc-800 rounded-lg text-sm text-theme-accent placeholder-zinc-500 focus:outline-none focus:border-theme-accent/50 focus:bg-zinc-900 transition-all font-semibold"
            disabled={isAnalyzing}
            id="ticker-search-input"
            autoComplete="off"
          />
          
          {/* Autocomplete Dropdown */}
          <AnimatePresence>
            {showSuggestions && suggestions.length > 0 && (
              <motion.div
                ref={dropdownRef}
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -5 }}
                transition={{ duration: 0.15 }}
                className="absolute top-full left-0 right-0 mt-2 bg-zinc-900 border border-zinc-800 rounded-lg shadow-xl shadow-black/40 overflow-hidden z-50"
              >
                {suggestions.map((s, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => handleSuggestionClick(s.symbol)}
                    className="w-full text-left px-4 py-2.5 hover:bg-zinc-800/80 transition-colors flex items-center justify-between group border-b border-zinc-800/50 last:border-0"
                  >
                    <div className="flex flex-col">
                      <span className="text-sm font-bold text-theme-accent group-hover:text-theme-accent transition-colors">{s.symbol}</span>
                      <span className="text-xs text-zinc-400 truncate max-w-[200px]">{s.name}</span>
                    </div>
                    <span className="text-[10px] uppercase font-semibold text-zinc-400 bg-zinc-950 px-2 py-1 rounded border border-zinc-800">{s.type}</span>
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        {isAnalyzing ? (
          <motion.button
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.98 }}
            type="button"
            onClick={(e) => { e.preventDefault(); e.stopPropagation(); onStopAnalysis(); }}
            className="flex items-center gap-1.5 px-4 py-2 text-sm font-bold rounded-lg text-red-200 bg-red-950/80 border border-red-900 hover:bg-red-900 transition-all duration-200 whitespace-nowrap shadow-md"
            id="stop-button"
          >
            <div className="w-3 h-3 rounded-sm bg-red-400" />
            Stop
          </motion.button>
        ) : (
          <motion.button
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.98 }}
            type="submit"
            disabled={!ticker.trim()}
            className="flex items-center gap-1.5 px-4 py-2 text-sm font-bold rounded-lg text-theme-bg bg-theme-accent hover:bg-[#e5d2b0] disabled:bg-zinc-800 disabled:text-zinc-500 disabled:opacity-100 disabled:cursor-not-allowed transition-all duration-200 whitespace-nowrap shadow-md shadow-theme-accent/10"
            id="analyze-button"
          >
            <Zap className="w-3.5 h-3.5 text-theme-bg" />
            Analyze
          </motion.button>
        )}
      </form>



      {/* Spacer */}
      <div className="flex-1" />

      <div className="flex items-center justify-between w-auto gap-4">
        {/* View toggle — only show when we have content */}
        {reportMarkdown && (
          <div className="flex bg-zinc-900/60 rounded-lg p-0.5 border border-zinc-800">
          <button
            onClick={() => onViewChange('report')}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all duration-200 ${
              activeView === 'report' 
                ? 'bg-theme-accent text-theme-bg shadow-sm font-bold' 
                : 'text-zinc-400 hover:text-theme-accent'
            }`}
            id="view-toggle-report"
          >
            Report
          </button>
          {hasValuationResults && (
            <button
              onClick={() => onViewChange('valuation')}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all duration-200 ${
                activeView === 'valuation' 
                  ? 'bg-theme-accent text-theme-bg shadow-sm font-bold' 
                  : 'text-zinc-400 hover:text-theme-accent'
              }`}
              id="view-toggle-valuation"
            >
              Calculations
            </button>
          )}
          {hasRawData && (
            <button
              onClick={() => onViewChange('raw')}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all duration-200 ${
                activeView === 'raw' 
                  ? 'bg-theme-accent text-theme-bg shadow-sm font-bold' 
                  : 'text-zinc-400 hover:text-theme-accent'
              }`}
              id="view-toggle-raw"
            >
              Raw Data
            </button>
          )}
        </div>
      )}

      {/* Export actions — only show when we have a report, hidden on mobile for space */}
      {reportMarkdown && activeView !== 'history' && (
        <div className="flex items-center gap-2 pr-2">
          <button
            onClick={handleExportMarkdown}
            disabled={isExporting}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-theme-accent hover:bg-zinc-800 bg-zinc-900/60 border border-zinc-800 rounded-lg transition-all duration-200"
            id="export-md-button"
          >
            <FileDown className="w-3.5 h-3.5" />
            MD
          </button>
          <button
            onClick={handleExportPdf}
            disabled={isExporting}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-bold text-theme-bg bg-theme-accent hover:bg-[#e5d2b0] disabled:opacity-60 border border-theme-accent/50 rounded-lg shadow-sm transition-all duration-200"
            id="export-pdf-button"
          >
            {isExporting ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-theme-bg" />
            ) : (
              <Download className="w-3.5 h-3.5" />
            )}
            {isExporting ? 'Exporting...' : 'PDF'}
          </button>
        </div>
      )}
      </div>
    </div>
  );
}
