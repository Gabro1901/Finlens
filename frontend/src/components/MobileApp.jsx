import { AnimatePresence, motion } from 'framer-motion';
import { MessageSquare, Loader2 } from 'lucide-react';
import BottomNav from './BottomNav';
import AnalysisOverlay from './AnalysisOverlay';
import MobileReportViewer from './MobileReportViewer';
import ChatPanel from './ChatPanel';
import HistoryView from './HistoryView';
import RawDataViewer from './RawDataViewer';
import SettingsModal from './SettingsModal';
import MobileHome from './MobileHome';

export default function MobileApp({
  isAnalyzing,
  reportMarkdown,
  currentStage,
  currentMessage,
  valuationStreaming,
  targetTicker,
  rawContextData,
  activeView,
  setActiveView,
  isSettingsOpen,
  setIsSettingsOpen,
  isChatOpen,
  setIsChatOpen,
  isHistoryOpen,
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
}) {
  const mainContentView = activeView === 'history' ? 'history' : activeView === 'raw' && rawContextData ? 'raw' : 'report';

  return (
    <div className="h-[100dvh] w-screen flex flex-col overflow-hidden relative bg-zinc-950">
      
      {/* ── Main Content Area ── */}
      <main className="flex-1 overflow-y-auto overflow-x-hidden w-full relative" style={{ paddingBottom: 'calc(var(--bottom-nav-height) + 24px)' }}>
        
        {/* Error state */}
        {currentStage === 'error' && (
          <div className="mx-4 mt-12 bg-red-950/60 border border-red-900/50 rounded-2xl p-5 text-red-300 relative z-50">
            <h3 className="font-semibold text-red-200 mb-2 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-red-500" /> Error
            </h3>
            <p className="text-sm">Analysis failed. Please try again.</p>
            <button onClick={handleClearAnalysis} className="mt-4 px-4 py-2 bg-red-900/50 rounded-lg text-sm text-red-200">Go Back</button>
          </div>
        )}

        {/* Empty state -> Mobile Home Dashboard */}
        {(activeView === 'home' || (!reportMarkdown && !isAnalyzing && currentStage !== 'error' && mainContentView !== 'history')) && (
          <MobileHome 
             onStartAnalysis={(ticker) => {
               setActiveView('report');
               handleStartAnalysis(ticker);
             }} 
             onOpenSettings={() => setIsSettingsOpen(true)}
          />
        )}

        {/* Views */}
        {reportMarkdown && mainContentView === 'report' && activeView !== 'home' && (
          <div className="animate-fade-in w-full">
            <MobileReportViewer markdown={reportMarkdown} ticker={targetTicker} onClear={() => setActiveView('home')} />
          </div>
        )}

        {rawContextData && mainContentView === 'raw' && (
          <div className="animate-fade-in w-full h-full p-4 pt-12">
            <RawDataViewer data={rawContextData} />
          </div>
        )}

        {mainContentView === 'history' && activeView !== 'home' && (
          <div className="animate-fade-in w-full h-full pt-safe-top mt-12">
            <HistoryView 
              historyList={historyList}
              isLoading={isHistoryLoading}
              onSelectHistory={handleSelectHistory}
              onDeleteHistory={handleDeleteHistory}
            />
          </div>
        )}
      </main>

      {/* ── View Toggle Pill (Floating at top when report is active) ── */}
      {(reportMarkdown || isAnalyzing) && mainContentView !== 'history' && activeView !== 'home' && (
        <div className="fixed top-3 left-1/2 -translate-x-1/2 z-50 bg-zinc-900/90 backdrop-blur-xl rounded-full p-1 border border-zinc-800 shadow-2xl flex items-center">
          <button
            onClick={() => setActiveView('report')}
            className={`px-5 py-1.5 rounded-full text-[13px] font-bold transition-all duration-200 ${
              activeView === 'report' ? 'bg-theme-accent text-theme-bg shadow-md' : 'text-zinc-400'
            }`}
          >
            Report
          </button>
          {rawContextData && (
            <button
              onClick={() => setActiveView('raw')}
              className={`px-5 py-1.5 rounded-full text-[13px] font-bold transition-all duration-200 ${
                activeView === 'raw' ? 'bg-theme-accent text-theme-bg shadow-md' : 'text-zinc-400'
              }`}
            >
              Raw Data
            </button>
          )}
          {isAnalyzing && (
            <button
              onClick={(e) => { e.preventDefault(); handleStopAnalysis(); }}
              className="px-4 py-1.5 ml-1 rounded-full text-[13px] font-bold bg-red-950/60 text-red-400 border border-red-900/50"
            >
              Stop
            </button>
          )}
        </div>
      )}

      {/* ── Mobile Bottom Navigation ── */}
      <BottomNav
        activeView={isChatOpen ? 'chat' : activeView}
        onNavigate={setActiveView}
        onOpenSettings={() => setIsSettingsOpen(true)}
        hasReport={!!reportMarkdown}
      />

      {/* ── Mobile Chat Bottom Sheet ── */}
      <AnimatePresence>
        {isChatOpen && (
          <div className="fixed inset-0 z-50 flex items-end">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
              onClick={() => setIsChatOpen(false)}
            />
            <motion.div
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className="relative w-full h-[85vh] bg-zinc-950 rounded-t-[2.5rem] overflow-hidden shadow-2xl flex flex-col border-t border-zinc-800"
            >
              <div className="w-full h-6 flex items-center justify-center shrink-0" onClick={() => setIsChatOpen(false)}>
                <div className="w-12 h-1.5 rounded-full bg-zinc-700" />
              </div>
              <div className="flex-1 overflow-hidden relative">
                <ChatPanel
                  isOpen={isChatOpen}
                  onClose={() => setIsChatOpen(false)}
                  ticker={targetTicker}
                  reportMarkdown={reportMarkdown}
                  rawContextData={rawContextData}
                  apiKey={apiKeys.openai}
                  isMobile={true}
                />
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* ── Floating Action Button (Chat) ── */}
      {reportMarkdown && !isChatOpen && (
        <button
          onClick={() => setIsChatOpen(true)}
          className="fixed right-6 w-14 h-14 rounded-[1.25rem] bg-theme-accent shadow-[0_8px_32px_rgba(248,231,201,0.25)] text-theme-bg border border-theme-accent/40 flex items-center justify-center z-40 active:scale-95 transition-transform"
          style={{ bottom: 'calc(var(--bottom-nav-height) + 24px)' }}
        >
          <MessageSquare className="w-6 h-6 text-theme-bg" />
        </button>
      )}

      {/* Overlay & Modals */}
      <AnalysisOverlay currentStage={isAnalyzing ? currentStage : null} currentMessage={currentMessage} ticker={targetTicker} reportMarkdown={reportMarkdown} valuationStreaming={valuationStreaming} />
      <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} apiKeys={apiKeys} setApiKeys={setApiKeys} language={language} setLanguage={setLanguage} />
    </div>
  );
}
