import { AnimatePresence } from 'framer-motion';
import { MessageSquare } from 'lucide-react';
import Sidebar from './Sidebar';
import CommandBar from './CommandBar';
import AnalysisOverlay from './AnalysisOverlay';
import ReportViewer from './ReportViewer';
import ChatPanel from './ChatPanel';
import HistoryView from './HistoryView';
import RawDataViewer from './RawDataViewer';
import ValuationCalculationsViewer from './ValuationCalculationsViewer';
import SettingsModal from './SettingsModal';

export default function DesktopApp({
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
  historyList,
  isHistoryLoading,
  apiKeys,
  setApiKeys,
  language,
  setLanguage,
  handleStartAnalysis,
  handleStopAnalysis,
  handleSelectHistory,
  handleDeleteHistory
}) {
  const mainContentView = activeView === 'history' ? 'history' : 
                          activeView === 'valuation' && valuationResultsData ? 'valuation' : 
                          activeView === 'raw' && rawContextData ? 'raw' : 
                          'report';

  return (
    <div className="h-[100dvh] w-screen flex overflow-hidden relative bg-zinc-950">
      {/* ── Ambient background glows ── */}
      <div className="fixed top-[-20%] left-[10%] w-[600px] h-[600px] rounded-full bg-theme-bg/40 blur-[150px] pointer-events-none" />
      <div className="fixed bottom-[-20%] right-[10%] w-[500px] h-[500px] rounded-full bg-theme-accent/[0.08] blur-[150px] pointer-events-none" />

      {/* ── Sidebar ── */}
      <Sidebar
        activeView={isChatOpen ? 'chat' : activeView}
        onNavigate={setActiveView}
        onOpenSettings={() => setIsSettingsOpen(true)}
        hasReport={!!reportMarkdown}
      />

      {/* ── Main Layout ── */}
      <div 
        className="flex h-full w-full" 
        style={{ paddingLeft: 'var(--sidebar-width)' }}
      >
        {/* Main Content Column */}
        <div className="flex-1 flex flex-col min-w-0 relative h-full w-full">
          {/* ── Command Bar ── */}
          <CommandBar
            onStartAnalysis={handleStartAnalysis}
            onStopAnalysis={handleStopAnalysis}
            isAnalyzing={isAnalyzing}
            currentStage={currentStage}
            currentMessage={currentMessage}
            reportMarkdown={reportMarkdown}
            ticker={targetTicker}
            activeView={activeView}
            onViewChange={setActiveView}
            hasRawData={!!rawContextData}
            hasValuationResults={!!valuationResultsData}
          />

          {/* ── Content area ── */}
          <main className="flex-1 overflow-y-auto overflow-x-hidden">
            {/* Error state */}
            {currentStage === 'error' && (
              <div className="max-w-3xl mx-auto mt-8 px-6">
                <div className="bg-red-950/40 border border-red-900/50 rounded-xl p-6 text-red-300 animate-fade-in">
                  <h3 className="font-semibold text-red-200 mb-2 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-red-400" />
                    Analysis Error
                  </h3>
                  <p className="text-sm">An error occurred during the pipeline. Check the browser console (F12) for details, or try again.</p>
                </div>
              </div>
            )}

            {/* Empty state — no report yet */}
            {!reportMarkdown && !isAnalyzing && currentStage !== 'error' && mainContentView !== 'history' && (
              <div className="flex-1 flex items-center justify-center h-full min-h-[400px]">
                <div className="text-center space-y-6 animate-fade-in max-w-md px-6">
                  <div className="w-20 h-20 mx-auto rounded-2xl bg-gradient-to-br from-theme-accent/20 to-theme-bg/40 border border-theme-accent/30 flex items-center justify-center shadow-lg shadow-theme-accent/5">
                    <svg className="w-10 h-10 text-theme-accent" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M12 2L2 7l10 5 10-5-10-5z" />
                      <path d="M2 17l10 5 10-5" />
                      <path d="M2 12l10 5 10-5" />
                    </svg>
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-theme-accent mb-2">Financial Intelligence</h2>
                    <p className="text-sm text-zinc-400 leading-relaxed">Enter a ticker symbol in the command bar above to generate a comprehensive AI-driven analysis report with accounting forensics, peer benchmarking, and forward-looking signals.</p>
                  </div>
                </div>
              </div>
            )}

            {/* Report view */}
            {reportMarkdown && mainContentView === 'report' && (
              <div className="animate-fade-in">
                <ReportViewer markdown={reportMarkdown} ticker={targetTicker} />
              </div>
            )}

            {/* Raw data view */}
            {rawContextData && mainContentView === 'raw' && (
              <div className="animate-fade-in h-full">
                <RawDataViewer data={rawContextData} />
              </div>
            )}

            {/* Valuation Calculations view */}
            {valuationResultsData && mainContentView === 'valuation' && (
              <div className="animate-fade-in h-full">
                <ValuationCalculationsViewer data={valuationResultsData} />
              </div>
            )}

            {/* History view */}
            {mainContentView === 'history' && (
              <div className="animate-fade-in h-full">
                <HistoryView 
                  historyList={historyList}
                  isLoading={isHistoryLoading}
                  onSelectHistory={handleSelectHistory}
                  onDeleteHistory={handleDeleteHistory}
                />
              </div>
            )}
          </main>
        </div>

        {/* ── Chat drawer ── */}
        <AnimatePresence>
          {isChatOpen && (
            <ChatPanel
              isOpen={isChatOpen}
              onClose={() => setIsChatOpen(false)}
              ticker={targetTicker}
              reportMarkdown={reportMarkdown}
              rawContextData={rawContextData}
              apiKey={apiKeys.openai}
            />
          )}
        </AnimatePresence>
      </div>

      {/* ── Analysis overlay ── */}
      <AnalysisOverlay currentStage={isAnalyzing ? currentStage : null} currentMessage={currentMessage} ticker={targetTicker} reportMarkdown={reportMarkdown} valuationStreaming={valuationStreaming} />

      {/* ── Settings modal ── */}
      <SettingsModal 
        isOpen={isSettingsOpen} 
        onClose={() => setIsSettingsOpen(false)} 
        apiKeys={apiKeys} 
        setApiKeys={setApiKeys} 
        language={language}
        setLanguage={setLanguage}
      />

      {/* ── Chat FAB ── */}
      {reportMarkdown && !isChatOpen && (
        <button
          onClick={() => setIsChatOpen(!isChatOpen)}
          className="fixed bottom-6 right-6 w-14 h-14 rounded-full bg-theme-accent hover:bg-[#e5d2b0] text-theme-bg shadow-xl shadow-theme-accent/20 flex items-center justify-center transition-all duration-200 z-50 hover:scale-105 active:scale-95 border border-theme-accent/40"
        >
          <MessageSquare className="w-6 h-6 text-theme-bg" />
        </button>
      )}
    </div>
  );
}
