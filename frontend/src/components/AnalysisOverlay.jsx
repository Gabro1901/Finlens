import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, Loader2 } from 'lucide-react';

const STAGES = [
  { id: 'init', label: 'Initializing', sublabel: 'Setting up pipeline' },
  { id: 'collection', label: 'Data Collection', sublabel: 'Fetching market data & filings' },
  { id: 'normalization', label: 'Normalizing', sublabel: 'Accounting adjustments' },
  { id: 'context', label: 'Context Assembly', sublabel: 'Building intelligence context' },
  { id: 'generation', label: 'Multi-Agent Analysis', sublabel: 'Running Optimistic and Pessimistic AI in parallel' },
  { id: 'synthesis', label: 'Synthesis', sublabel: 'Adjudicating report' },
  { id: 'valuation', label: 'Quantitative Valuation', sublabel: 'Selecting models & computing targets' },
  { id: 'complete', label: 'Complete', sublabel: 'Analysis ready' },
];

export default function AnalysisOverlay({ currentStage, currentMessage, ticker, reportMarkdown, valuationStreaming }) {
  if (!currentStage || currentStage === 'complete' || currentStage === 'error' || currentStage === 'cancelled' ||
      (currentStage === 'synthesis' && reportMarkdown && reportMarkdown.length > 0) ||
      (currentStage === 'valuation' && valuationStreaming)) return null;

  const currentIndex = STAGES.findIndex(s => s.id === currentStage);
  const currentStageData = STAGES[currentIndex] || STAGES[0];
  const progress = currentIndex >= 0 ? ((currentIndex + 0.5) / STAGES.length) * 100 : 0;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.4 }}
        className="fixed inset-0 z-30 flex items-center justify-center"
        style={{ left: 'var(--sidebar-width)' }}
      >
        {/* Backdrop */}
        <div className="absolute inset-0 bg-[#03241b]/90 backdrop-blur-sm" />
        
        {/* Animated background orbs */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px]">
            <div className="absolute inset-0 rounded-full bg-theme-accent/5 animate-pulse-glow" />
            <div className="w-3 h-3 rounded-full bg-theme-accent/40 animate-orbit absolute top-1/2 left-1/2" />
            <div className="w-2 h-2 rounded-full bg-theme-bg animate-orbit-reverse absolute top-1/2 left-1/2" />
          </div>
        </div>

        {/* Center content */}
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ delay: 0.15, duration: 0.5 }}
          className="relative z-10 flex flex-col items-center gap-8 max-w-sm text-center"
        >
          {/* Progress ring */}
          <div className="relative w-28 h-28">
            {/* Track */}
            <svg className="w-28 h-28 -rotate-90" viewBox="0 0 112 112">
              <circle
                cx="56" cy="56" r="48"
                fill="none"
                stroke="rgba(248,231,201,0.15)"
                strokeWidth="4"
              />
              <motion.circle
                cx="56" cy="56" r="48"
                fill="none"
                stroke="url(#progress-gradient)"
                strokeWidth="4"
                strokeLinecap="round"
                strokeDasharray={2 * Math.PI * 48}
                initial={{ strokeDashoffset: 2 * Math.PI * 48 }}
                animate={{ strokeDashoffset: 2 * Math.PI * 48 * (1 - progress / 100) }}
                transition={{ duration: 0.8, ease: 'easeInOut' }}
              />
              <defs>
                <linearGradient id="progress-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="var(--theme-bg)" />
                  <stop offset="100%" stopColor="var(--theme-accent)" />
                </linearGradient>
              </defs>
            </svg>
            {/* Center icon */}
            <div className="absolute inset-0 flex items-center justify-center">
              <Loader2 className="w-8 h-8 text-theme-accent animate-spin" strokeWidth={1.5} />
            </div>
          </div>

          {/* Ticker badge */}
          {ticker && (
            <div className="px-4 py-1.5 rounded-full bg-theme-bg border border-theme-accent/30 text-theme-accent text-sm font-data font-semibold tracking-wider shadow-lg">
              {ticker}
            </div>
          )}

          {/* Stage info */}
          <div className="space-y-2">
            <motion.h2
              key={currentStageData.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-xl font-bold text-theme-accent"
            >
              {currentStageData.label}
            </motion.h2>
            <motion.p
              key={currentStageData.id + '-sub'}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="text-sm text-zinc-400 max-w-[280px] mx-auto leading-relaxed"
            >
              {currentMessage || currentStageData.sublabel}
            </motion.p>
          </div>

          {/* Stage dots */}
          <div className="flex items-center gap-2">
            {STAGES.slice(0, -1).map((stage, idx) => {
              const isCompleted = idx < currentIndex;
              const isCurrent = idx === currentIndex;
              return (
                <div
                  key={stage.id}
                  className={`w-2.5 h-2.5 rounded-full transition-all duration-300 ${
                    isCurrent ? 'scale-125 shadow-lg shadow-theme-accent/40' : ''
                  }`}
                  style={{
                    backgroundColor: isCompleted || isCurrent ? 'var(--theme-accent)' : 'var(--theme-surface)',
                    opacity: isCompleted || isCurrent ? 1 : 0.4
                  }}
                />
              );
            })}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
