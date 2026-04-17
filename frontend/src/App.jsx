import { useState, useEffect } from 'react';
import './index.css';
import { Play, Sparkles, ExternalLink, ChevronLeft, ChevronRight, Loader2, Database, Info, Users, Activity, Target } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL;

export default function App() {
  const [leads, setLeads] = useState([]);
  const [meta, setMeta] = useState({ total: 0, skip: 0, limit: 20 });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [analysis, setAnalysis] = useState("");
  const [analyzing, setAnalyzing] = useState(false);

  const fetchLeads = async (skip = 0) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/leads?skip=${skip}&limit=${meta.limit}`);
      const data = await res.json();
      setLeads(data.data);
      setMeta(data.metadata);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchLeads(0);
  }, []);

  const triggerPipeline = async () => {
    setMessage("Starting YC pipeline in background.");
    try {
      const res = await fetch(`${API_BASE}/api/pipeline/start`, { method: 'POST' });
      const data = await res.json();
      setMessage(data.message);
      setTimeout(() => setMessage(""), 5000);
    } catch (err) {
      setMessage("Pipeline failed to start.");
    }
  };

  const runAnalysis = async () => {
    setAnalyzing(true);
    setAnalysis("Analyzing current database records with LLM...");
    try {
      const res = await fetch(`${API_BASE}/api/analyze`);
      const data = await res.json();
      setAnalysis(data.analysis);
    } catch (err) {
      setAnalysis("Analysis request failed.");
    }
    setAnalyzing(false);
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 font-sans selection:bg-emerald-500/30">
      <header className="bg-zinc-900 border-b border-zinc-800 sticky top-0 z-10 shadow-lg">
        <div className="max-w-7xl mx-auto px-6 py-4 flex flex-col sm:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="bg-gradient-to-br from-emerald-400 to-cyan-500 p-2 rounded-lg text-zinc-950 shadow-md">
              <Database size={24} />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white">YC Leads Intelligence</h1>
          </div>
          <div className="flex gap-3 w-full sm:w-auto">
            <button 
              onClick={triggerPipeline} 
              className="flex-1 sm:flex-none flex items-center justify-center gap-2 bg-zinc-800 hover:bg-zinc-700 text-emerald-400 font-bold py-2 px-4 rounded-lg transition-colors border border-zinc-700"
            >
              <Play size={18} />
              Run Scraper
            </button>
            <button 
              onClick={runAnalysis} 
              disabled={analyzing} 
              className="flex-1 sm:flex-none flex items-center justify-center gap-2 bg-gradient-to-r from-emerald-500 to-cyan-500 hover:from-emerald-400 hover:to-cyan-400 disabled:opacity-50 text-zinc-950 font-bold py-2 px-4 rounded-lg shadow-md transition-all"
            >
              {analyzing ? <Loader2 size={18} className="animate-spin" /> : <Sparkles size={18} />}
              Analyze Market
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-zinc-900 border border-zinc-800 p-6 rounded-xl flex items-center gap-4 shadow-sm">
            <div className="bg-emerald-500/10 p-3 rounded-lg text-emerald-400"><Users size={28} /></div>
            <div>
              <p className="text-zinc-400 text-sm font-semibold uppercase">Total Leads</p>
              <h3 className="text-2xl font-bold text-white">{meta.total}</h3>
            </div>
          </div>
          <div className="bg-zinc-900 border border-zinc-800 p-6 rounded-xl flex items-center gap-4 shadow-sm">
            <div className="bg-cyan-500/10 p-3 rounded-lg text-cyan-400"><Activity size={28} /></div>
            <div>
              <p className="text-zinc-400 text-sm font-semibold uppercase">Pipeline Status</p>
              <h3 className="text-2xl font-bold text-white">Active</h3>
            </div>
          </div>
          <div className="bg-zinc-900 border border-zinc-800 p-6 rounded-xl flex items-center gap-4 shadow-sm">
            <div className="bg-purple-500/10 p-3 rounded-lg text-purple-400"><Target size={28} /></div>
            <div>
              <p className="text-zinc-400 text-sm font-semibold uppercase">AI Insights</p>
              <h3 className="text-2xl font-bold text-white">{analysis ? "Generated" : "Pending"}</h3>
            </div>
          </div>
        </div>

        {message && (
          <div className="mb-6 flex items-center gap-3 p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
            <Info size={20} />
            <p className="font-bold">{message}</p>
          </div>
        )}

        {analysis && (
          <div className="mb-8 p-6 bg-zinc-900 rounded-xl border border-zinc-800 shadow-md">
            <div className="flex items-center gap-2 mb-4 text-cyan-400">
              <Sparkles size={20} />
              <h2 className="text-lg font-bold text-white">LLM Market Analysis</h2>
            </div>
            <div className="prose prose-invert max-w-none">
              <p className="text-zinc-300 leading-relaxed whitespace-pre-wrap">{analysis}</p>
            </div>
          </div>
        )}

        <div className="bg-zinc-900 rounded-xl border border-zinc-800 overflow-hidden shadow-md">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-zinc-800">
              <thead className="bg-zinc-950/50">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-bold text-zinc-400 uppercase tracking-wider">Company</th>
                  <th className="px-6 py-4 text-left text-xs font-bold text-zinc-400 uppercase tracking-wider">Industry</th>
                  <th className="px-6 py-4 text-left text-xs font-bold text-zinc-400 uppercase tracking-wider">Profile</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800 bg-zinc-900">
                {loading ? (
                  <tr>
                    <td colSpan="3" className="px-6 py-12 text-center">
                      <Loader2 size={32} className="animate-spin mx-auto text-emerald-500 mb-2" />
                      <p className="text-zinc-400 font-bold">Loading data...</p>
                    </td>
                  </tr>
                ) : leads.length === 0 ? (
                  <tr>
                    <td colSpan="3" className="px-6 py-12 text-center text-zinc-500 font-bold">
                      No leads found. Run the scraper.
                    </td>
                  </tr>
                ) : (
                  leads.map((lead, idx) => (
                    <tr key={idx} className="hover:bg-zinc-800/50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="font-bold text-white">{lead.company_name}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-bold bg-zinc-800 text-cyan-400 border border-zinc-700">
                          {lead.industry}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <a 
                          href={lead.yc_url} 
                          target="_blank" 
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-emerald-400 hover:text-emerald-300 font-bold transition-colors"
                        >
                          Visit Profile <ExternalLink size={14} />
                        </a>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          
          <div className="px-6 py-4 border-t border-zinc-800 bg-zinc-950/50 flex items-center justify-between">
            <button 
              disabled={meta.skip === 0 || loading} 
              onClick={() => fetchLeads(meta.skip - meta.limit)} 
              className="inline-flex items-center gap-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 disabled:opacity-50 px-3 py-1.5 rounded-lg text-sm font-bold border border-zinc-700 transition-colors"
            >
              <ChevronLeft size={16} /> Prev
            </button>
            <span className="text-sm font-bold text-zinc-400">
              Page {Math.floor(meta.skip / meta.limit) + 1} of {Math.ceil(meta.total / meta.limit) || 1}
            </span>
            <button 
              disabled={meta.skip + meta.limit >= meta.total || loading} 
              onClick={() => fetchLeads(meta.skip + meta.limit)} 
              className="inline-flex items-center gap-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 disabled:opacity-50 px-3 py-1.5 rounded-lg text-sm font-bold border border-zinc-700 transition-colors"
            >
              Next <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}