import { useState } from 'react';
import { Calculator, ChevronDown, ChevronRight, AlertTriangle, CheckCircle2, TrendingUp, Info } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const JsonViewer = ({ data, defaultExpanded = false }) => {
  const [expanded, setExpanded] = useState(defaultExpanded);

  if (typeof data !== 'object' || data === null) {
    return <span className="text-theme-accent font-data text-xs">{JSON.stringify(data)}</span>;
  }

  const isArray = Array.isArray(data);
  const keys = Object.keys(data);

  if (keys.length === 0) {
    return <span className="text-zinc-500 font-data text-xs">{isArray ? '[]' : '{}'}</span>;
  }

  return (
    <div className="font-data text-xs">
      <button 
        onClick={() => setExpanded(!expanded)} 
        className="flex items-center gap-1 hover:text-theme-accent transition-colors text-zinc-400"
      >
        {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        <span>{isArray ? 'Array' : 'Object'}</span>
        <span className="text-zinc-500 text-[10px] ml-1">({keys.length} items)</span>
      </button>
      
      {expanded && (
        <div className="pl-4 mt-1 border-l border-zinc-800/50 space-y-1">
          {keys.map(key => (
            <div key={key} className="flex flex-col sm:flex-row sm:items-baseline gap-1 sm:gap-2">
              <span className="text-theme-accent min-w-fit font-medium">
                {isArray ? `[${key}]` : `"${key}"`}:
              </span>
              <div className="overflow-x-auto pb-1">
                <JsonViewer data={data[key]} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const FORMULAS = {
  dcf: "Implied EV = Σ (FCF_t / (1 + WACC)^t) + Terminal Value / (1 + WACC)^n",
  sotp: "Implied EV = Σ (Segment Metric × Segment Multiple)",
  comps: "Implied Price = Median Peer Multiple × Company Metric (Quality Adj. Optional)",
  ddm: "Fair Value = Σ (DPS_t / (1 + COE)^t) + Terminal Value / (1 + COE)^n",
  ev_revenue: "Implied EV = Target EV/Revenue × Forward Revenue",
  ev_ebitda: "Implied EV = Target EV/EBITDA × Forward EBITDA",
  pe_target: "Implied Price = Target P/E × Forward EPS",
  nav: "Implied Price = Book Value Per Share × Target P/B"
};

const formatLargeNumber = (num) => {
  if (num === null || num === undefined) return 'N/A';
  if (num >= 1e12 || num <= -1e12) return (num / 1e12).toFixed(2) + 'T';
  if (num >= 1e9 || num <= -1e9) return (num / 1e9).toFixed(2) + 'B';
  if (num >= 1e6 || num <= -1e6) return (num / 1e6).toFixed(2) + 'M';
  if (num >= 1e3 || num <= -1e3) return (num / 1e3).toFixed(2) + 'K';
  return num.toFixed(2);
};

export default function ValuationCalculationsViewer({ data }) {
  if (!data) return null;

  const { business_profile = {}, model_results = {}, blended_target, current_price } = data;
  
  // Calculate blended upside/downside
  const hasBlended = blended_target !== undefined && blended_target !== null;
  const blendedUpside = hasBlended && current_price ? ((blended_target / current_price) - 1) * 100 : 0;
  const isPositive = blendedUpside >= 0;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-6 lg:px-12 xl:px-20 pt-8 pb-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-theme-accent/15 flex items-center justify-center border border-theme-accent/30 shadow-[0_0_15px_rgba(248,231,201,0.1)]">
            <Calculator className="w-4 h-4 text-theme-accent" />
          </div>
          <div>
            <h2 className="text-base font-bold text-theme-accent">Valuation Dashboard</h2>
            <p className="text-xs text-zinc-400">Quantitative engine outputs and parameters</p>
          </div>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto px-6 lg:px-12 xl:px-20 pb-16 space-y-6">
        
        {/* Top Summary Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          
          {/* Target Price Card */}
          <div className="bg-zinc-900/60 rounded-2xl border border-zinc-800/60 overflow-hidden relative group p-6 flex flex-col justify-center min-h-[140px] shadow-lg shadow-black/20">
            <div className="absolute inset-0 bg-gradient-to-br from-theme-accent/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <div className="relative z-10 flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold text-zinc-400 uppercase tracking-widest mb-1">Blended Target Price</p>
                <div className="flex items-baseline gap-3">
                  <span className="text-4xl font-black text-theme-accent tracking-tight">
                    {hasBlended ? `$${blended_target.toFixed(2)}` : 'N/A'}
                  </span>
                  {hasBlended && current_price > 0 && (
                    <span className={`text-sm font-bold flex items-center gap-1 ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                      {isPositive ? '+' : ''}{blendedUpside.toFixed(1)}%
                    </span>
                  )}
                </div>
              </div>
              <div className="w-10 h-10 rounded-full bg-zinc-950 border border-zinc-800 flex items-center justify-center text-zinc-500 shadow-inner">
                <TrendingUp className="w-5 h-5" />
              </div>
            </div>
          </div>

          {/* Business Profile Card */}
          <div className="bg-zinc-900/60 rounded-2xl border border-zinc-800/60 p-5 flex flex-col shadow-lg shadow-black/20">
            <p className="text-xs font-semibold text-zinc-400 uppercase tracking-widest mb-3 flex items-center gap-2">
              <Info className="w-3.5 h-3.5" /> Business Profile Context
            </p>
            <div className="space-y-3">
              <div className="flex justify-between items-center text-sm border-b border-zinc-800/50 pb-2">
                <span className="text-zinc-500 font-medium">Business Type</span>
                <span className="text-zinc-200 capitalize font-semibold">{business_profile.type?.replace(/_/g, ' ') || 'Unknown'}</span>
              </div>
              <div className="flex justify-between items-center text-sm border-b border-zinc-800/50 pb-2">
                <span className="text-zinc-500 font-medium">Lifecycle Stage</span>
                <span className="text-zinc-200 capitalize font-semibold">{business_profile.lifecycle_stage?.replace(/_/g, ' ') || 'Unknown'}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Model Results Grid */}
        <div>
          <h3 className="text-sm font-bold text-zinc-300 mb-4 px-1 uppercase tracking-wide">Model Execution Details</h3>
          <div className="grid grid-cols-1 gap-4">
            {Object.entries(model_results).map(([key, result]) => {
              const hasError = !!result.error;
              const modelKey = result.model || key.replace('_target', '').replace('comps_cross_check', 'comps');
              const modelName = modelKey.toUpperCase();
              const price = result.results?.implied_price || result.results?.blended_price || result.results?.fair_value;
              const weight = result.weight || 0;
              const formula = FORMULAS[modelKey.toLowerCase()] || "Formula not specified for this model.";
              
              return (
                <div key={key} className={`rounded-xl border p-5 transition-all duration-300 ${
                  hasError 
                    ? 'bg-red-950/20 border-red-900/40 hover:border-red-800/60' 
                    : 'bg-zinc-900/40 border-zinc-800/80 hover:border-theme-accent/30 hover:shadow-lg hover:shadow-theme-accent/5'
                }`}>
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      {hasError ? (
                        <div className="w-8 h-8 rounded-full bg-red-950 border border-red-900/50 flex items-center justify-center">
                          <AlertTriangle className="w-4 h-4 text-red-400" />
                        </div>
                      ) : (
                        <div className="w-8 h-8 rounded-full bg-zinc-950 border border-zinc-800 flex items-center justify-center">
                          <CheckCircle2 className="w-4 h-4 text-green-500" />
                        </div>
                      )}
                      <div>
                        <h4 className={`text-sm font-bold capitalize ${hasError ? 'text-red-200' : 'text-zinc-200'}`}>
                          {key.replace(/_/g, ' ')} <span className="text-zinc-500 font-normal ml-1">({modelName})</span>
                        </h4>
                        <p className="text-[11px] text-zinc-500 font-medium">Weight in blend: {(weight * 100).toFixed(0)}%</p>
                      </div>
                    </div>
                    
                    {!hasError && price !== undefined && (
                      <div className="text-right">
                        <span className="block text-[10px] uppercase font-bold text-zinc-500 tracking-wider">Implied Price</span>
                        <span className="text-lg font-bold text-theme-accent">${price.toFixed(2)}</span>
                      </div>
                    )}
                  </div>

                  {hasError ? (
                    <div className="mt-3 text-sm text-red-300/90 bg-red-950/30 p-3 rounded-lg border border-red-900/30 font-medium leading-relaxed">
                      Error: {result.error}
                    </div>
                  ) : (
                    <div className="mt-4 pt-4 border-t border-zinc-800/50">
                      <div className="mb-4 p-2.5 rounded-lg bg-zinc-950/60 border border-zinc-800/40">
                        <p className="text-[10px] text-zinc-500 font-mono tracking-wide">
                          <span className="text-theme-accent/70 font-semibold mr-2">FORMULA:</span>
                          {formula}
                        </p>
                      </div>
                      <p className="text-xs font-semibold text-zinc-400 mb-2 uppercase tracking-wide">Key Parameters & Outputs</p>
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                        {Object.entries(result.results || {})
                          .filter(([k, v]) => !['implied_price', 'blended_price', 'upside_pct', 'current_price', 'scenarios', 'segments', 'metrics_computed', 'peer_details', 'peer_tickers_used'].includes(k))
                          .map(([k, v]) => (
                            <div key={k} className="bg-zinc-950/50 rounded-lg p-3 border border-zinc-800/30">
                              <span className="block text-[10px] text-zinc-500 font-semibold uppercase tracking-wider mb-1 truncate">{k.replace(/_/g, ' ')}</span>
                              <span className="block text-xs font-medium text-zinc-300 truncate">
                                {typeof v === 'number' ? 
                                  (k.includes('pct') || k.includes('growth') || k.includes('rate') || k.includes('wacc') || k.includes('margin') ? `${(v * 100).toFixed(2)}%` : 
                                   v > 1000 ? v.toLocaleString(undefined, {maximumFractionDigits: 0}) : v.toFixed(2)) 
                                  : String(v)}
                              </span>
                            </div>
                          ))
                        }
                      </div>

                      {/* Complex fields renderers */}
                      {result.results?.scenarios && (
                        <div className="mt-6">
                          <p className="text-xs font-semibold text-zinc-400 mb-2 uppercase tracking-wide">DCF Scenarios</p>
                          <div className="space-y-3">
                            {result.results.scenarios.map((scenario, idx) => (
                              <div key={idx} className="bg-zinc-950/40 rounded-xl border border-zinc-800/40 p-4">
                                <div className="flex justify-between items-center mb-3">
                                  <span className="font-bold text-sm text-theme-accent capitalize">{scenario.name || `Scenario ${idx+1}`}</span>
                                  <span className="text-xs bg-theme-accent/10 text-theme-accent px-2 py-1 rounded-md font-medium">
                                    {(scenario.probability * 100).toFixed(0)}% Weight
                                  </span>
                                </div>
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
                                  <div>
                                    <span className="block text-zinc-500 mb-1">Terminal FCF</span>
                                    <span className="font-medium text-zinc-300">${formatLargeNumber(scenario.terminal_year_fcf)}</span>
                                  </div>
                                  <div>
                                    <span className="block text-zinc-500 mb-1">Terminal Value</span>
                                    <span className="font-medium text-zinc-300">${formatLargeNumber(scenario.terminal_value)}</span>
                                  </div>
                                  <div>
                                    <span className="block text-zinc-500 mb-1">Enterprise Value</span>
                                    <span className="font-medium text-zinc-300">${formatLargeNumber(scenario.enterprise_value)}</span>
                                  </div>
                                  <div>
                                    <span className="block text-zinc-500 mb-1">Implied Price</span>
                                    <span className="font-bold text-theme-accent">${scenario.implied_price?.toFixed(2)}</span>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {result.results?.segments && (
                        <div className="mt-6">
                          <p className="text-xs font-semibold text-zinc-400 mb-2 uppercase tracking-wide">SOTP Segments</p>
                          <div className="space-y-3">
                            {result.results.segments.map((seg, idx) => (
                              <div key={idx} className="bg-zinc-950/40 rounded-xl border border-zinc-800/40 p-3 flex justify-between items-center text-xs">
                                <span className="font-bold text-zinc-200 capitalize">{seg.name}</span>
                                <div className="flex gap-4">
                                  <span className="text-zinc-400">Mult: <span className="text-zinc-200">{seg.multiple_range?.[0]}x - {seg.multiple_range?.[1]}x</span></span>
                                  <span className="text-zinc-400">EV: <span className="text-zinc-200">${formatLargeNumber(seg.ev_mid)}</span></span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {result.results?.metrics_computed && (
                        <div className="mt-6">
                          <p className="text-xs font-semibold text-zinc-400 mb-2 uppercase tracking-wide">Comps Metrics</p>
                          <div className="space-y-3">
                            {Object.entries(result.results.metrics_computed).map(([metricKey, metricResult]) => (
                              <div key={metricKey} className="bg-zinc-950/40 rounded-xl border border-zinc-800/40 p-3 flex justify-between items-center text-xs">
                                <span className="font-bold text-zinc-200 uppercase">{metricKey.replace('_', '/')}</span>
                                <div className="flex gap-4">
                                  <span className="text-zinc-400">Peer Median: <span className="text-zinc-200">{metricResult.peer_median_multiple?.toFixed(2) || metricResult.peer_median_pe?.toFixed(2)}x</span></span>
                                  <span className="text-zinc-400">Implied Price: <span className="text-theme-accent font-bold">${(metricResult.implied_price_quality_adjusted || metricResult.implied_price_unadjusted || metricResult.implied_price || 0).toFixed(2)}</span></span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Raw Payload Collapsible */}
        <div className="mt-12 pt-8 border-t border-zinc-800/60">
          <details className="group">
            <summary className="flex items-center gap-2 text-sm font-semibold text-zinc-400 cursor-pointer hover:text-theme-accent transition-colors select-none">
              <ChevronRight className="w-4 h-4 group-open:rotate-90 transition-transform" />
              View Raw JSON Payload
            </summary>
            <div className="mt-4 p-4 bg-zinc-950/80 rounded-xl border border-zinc-800/50 overflow-x-auto">
              <JsonViewer data={data} defaultExpanded={false} />
            </div>
          </details>
        </div>

      </div>
    </div>
  );
}
