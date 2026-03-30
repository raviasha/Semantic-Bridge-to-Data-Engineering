import { useState, useRef, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Send, GitBranch, AlertTriangle, CheckCircle, XCircle, Database, ChevronDown, ChevronRight } from 'lucide-react';
import { api } from '../api';

interface Turn {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  extracted_entities?: any[];
  confidence_factors?: Record<string, number>;
}

interface Entity {
  term: string;
  candidates?: string[];
  resolved: boolean;
  selected?: string;
  filter_value?: any;
}

export function InterviewPage() {
  const { interviewId } = useParams<{ interviewId: string }>();
  const navigate = useNavigate();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [score, setScore] = useState(0);
  const [factors, setFactors] = useState<Record<string, number>>({});
  const [entities, setEntities] = useState<Entity[]>([]);
  const [status, setStatus] = useState('in_progress');
  const [schemaOpen, setSchemaOpen] = useState(false);
  const [tables, setTables] = useState<any[]>([]);
  const [expandedTable, setExpandedTable] = useState<string | null>(null);
  const [tableDetails, setTableDetails] = useState<Record<string, any>>({});
  const messagesEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Load interview state
    if (interviewId) {
      api.getInterview(interviewId).then((data: any) => {
        if (data.turns) setTurns(data.turns);
        if (data.confidence_score) setScore(data.confidence_score);
        if (data.confidence_factors) setFactors(data.confidence_factors);
        if (data.entities) setEntities(data.entities);
        if (data.status) setStatus(data.status);
      }).catch(() => {});
    }
    // Load schema for sidebar
    api.listTables().then((data: any) => {
      if (data.tables) setTables(data.tables);
    }).catch(() => {});
  }, [interviewId]);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [turns]);

  const handleSend = async () => {
    if (!input.trim() || sending || !interviewId) return;
    const msg = input;
    setInput('');
    setSending(true);

    // Optimistic user message
    setTurns((prev) => [...prev, { role: 'user', content: msg }]);

    try {
      const data = await api.sendMessage(interviewId, msg);
      setTurns((prev) => [...prev, { role: 'assistant', content: data.assistant_turn.content }]);
      setScore(data.confidence_score);
      setFactors(data.confidence_factors);
      setEntities(data.entities || []);
      setStatus(data.status);
    } catch {
      setTurns((prev) => [
        ...prev,
        { role: 'assistant', content: '⚠️ Backend not reachable. Start the API server to get AI responses.' },
      ]);
    } finally {
      setSending(false);
    }
  };

  const toggleTable = async (tableName: string) => {
    if (expandedTable === tableName) {
      setExpandedTable(null);
      return;
    }
    setExpandedTable(tableName);
    if (!tableDetails[tableName]) {
      try {
        const detail = await api.getTable(tableName);
        setTableDetails((prev) => ({ ...prev, [tableName]: detail }));
      } catch {
        // ignore
      }
    }
  };

  const scoreColor = score >= 80 ? 'text-green-400' : score >= 60 ? 'text-yellow-400' : 'text-red-400';
  const scoreBarColor = score >= 80 ? 'bg-green-500' : score >= 60 ? 'bg-yellow-500' : 'bg-red-500';

  return (
    <div className="flex h-full">
      {/* Chat area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="px-6 py-3 border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h2 className="font-semibold">Interview</h2>
            <span className={`text-xs px-2 py-0.5 rounded-full border ${
              status === 'ready' ? 'bg-green-900/50 text-green-300 border-green-700' :
              status === 'needs_review' ? 'bg-yellow-900/50 text-yellow-300 border-yellow-700' :
              'bg-blue-900/50 text-blue-300 border-blue-700'
            }`}>
              {status.replace('_', ' ')}
            </span>
          </div>
          <div className="flex items-center gap-3">
            {score >= 60 && (
              <button
                onClick={() => navigate(`/interview/${interviewId}/flow`)}
                className="flex items-center gap-2 px-3 py-1.5 bg-[var(--color-primary)] text-white rounded-lg text-sm hover:bg-[var(--color-primary-dark)] transition-colors"
              >
                <GitBranch size={14} />
                View Flow Diagram
              </button>
            )}
            {score >= 80 && (
              <button
                onClick={() => navigate(`/interview/${interviewId}/review`)}
                className="flex items-center gap-2 px-3 py-1.5 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 transition-colors"
              >
                Generate SQL
              </button>
            )}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {turns.length === 0 && (
            <div className="text-center py-16">
              <p className="text-[var(--color-text-muted)]">
                Describe the metric or report you need in business terms.
              </p>
              <p className="text-sm text-[var(--color-text-muted)] mt-2">
                The AI will ask clarifying questions to build precise requirements.
              </p>
            </div>
          )}
          {turns.map((turn, i) => (
            <div
              key={i}
              className={`flex ${turn.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                  turn.role === 'user'
                    ? 'bg-[var(--color-primary)] text-white rounded-br-md'
                    : 'bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-bl-md'
                }`}
              >
                {turn.content}
              </div>
            </div>
          ))}
          {sending && (
            <div className="flex justify-start">
              <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] px-4 py-3 rounded-2xl rounded-bl-md">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-[var(--color-text-muted)] rounded-full animate-bounce" style={{animationDelay: '0ms'}} />
                  <span className="w-2 h-2 bg-[var(--color-text-muted)] rounded-full animate-bounce" style={{animationDelay: '150ms'}} />
                  <span className="w-2 h-2 bg-[var(--color-text-muted)] rounded-full animate-bounce" style={{animationDelay: '300ms'}} />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEnd} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-[var(--color-border)]">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Describe your metric or answer the AI's questions..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
              className="flex-1 px-4 py-2.5 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)]"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || sending}
              className="px-4 py-2.5 bg-[var(--color-primary)] text-white rounded-lg hover:bg-[var(--color-primary-dark)] disabled:opacity-50 transition-colors"
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>

      {/* Right sidebar — Confidence + Entities + Schema */}
      <aside className="w-80 border-l border-[var(--color-border)] bg-[var(--color-bg-secondary)] overflow-y-auto">
        {/* Confidence Score */}
        <div className="p-4 border-b border-[var(--color-border)]">
          <h3 className="text-sm font-semibold mb-3 text-[var(--color-text-muted)] uppercase tracking-wide">
            Confidence Score
          </h3>
          <div className="flex items-baseline gap-2 mb-3">
            <span className={`text-3xl font-bold ${scoreColor}`}>{score}</span>
            <span className="text-[var(--color-text-muted)]">/ 100</span>
          </div>
          <div className="w-full h-2 bg-[var(--color-bg-tertiary)] rounded-full overflow-hidden mb-4">
            <div
              className={`h-full ${scoreBarColor} rounded-full transition-all duration-500`}
              style={{ width: `${score}%` }}
            />
          </div>

          {/* Factor breakdown */}
          <div className="space-y-2">
            {Object.entries(factors).map(([key, val]) => (
              <div key={key} className="flex items-center justify-between text-xs">
                <span className="text-[var(--color-text-muted)] capitalize">
                  {key.replace(/_/g, ' ')}
                </span>
                <div className="flex items-center gap-2">
                  <div className="w-16 h-1.5 bg-[var(--color-bg-tertiary)] rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        val >= 0.7 ? 'bg-green-500' : val >= 0.4 ? 'bg-yellow-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${val * 100}%` }}
                    />
                  </div>
                  <span className="w-8 text-right">{Math.round(val * 100)}%</span>
                </div>
              </div>
            ))}
          </div>

          {/* Submission status */}
          <div className="mt-4 p-2 rounded-lg text-xs">
            {score >= 80 ? (
              <div className="flex items-center gap-2 text-green-400">
                <CheckCircle size={14} /> Ready for implementation
              </div>
            ) : score >= 60 ? (
              <div className="flex items-center gap-2 text-yellow-400">
                <AlertTriangle size={14} /> Needs review — can submit
              </div>
            ) : factors.entity_resolution === 0 || factors.grain_clarity === 0 ? (
              <div className="flex items-center gap-2 text-red-400">
                <XCircle size={14} /> Submission blocked — critical factors at 0
              </div>
            ) : (
              <div className="flex items-center gap-2 text-red-400">
                <XCircle size={14} /> Score too low — keep clarifying
              </div>
            )}
          </div>
        </div>

        {/* Resolved Entities */}
        <div className="p-4 border-b border-[var(--color-border)]">
          <h3 className="text-sm font-semibold mb-3 text-[var(--color-text-muted)] uppercase tracking-wide">
            Resolved Entities
          </h3>
          {entities.length === 0 ? (
            <p className="text-xs text-[var(--color-text-muted)]">No entities resolved yet</p>
          ) : (
            <div className="space-y-2">
              {entities.map((ent, i) => (
                <div key={i} className="text-xs p-2 bg-[var(--color-bg-tertiary)] rounded-lg">
                  <div className="flex items-center gap-2">
                    {ent.resolved ? (
                      <CheckCircle size={12} className="text-green-400 shrink-0" />
                    ) : (
                      <AlertTriangle size={12} className="text-yellow-400 shrink-0" />
                    )}
                    <span className="font-medium">"{ent.term}"</span>
                  </div>
                  {ent.selected && (
                    <p className="mt-1 text-[var(--color-text-muted)] ml-5 font-mono text-[10px]">
                      → {ent.selected}
                      {ent.filter_value && (
                        <span className="text-[var(--color-primary-light)]">
                          {' '}= {JSON.stringify(ent.filter_value)}
                        </span>
                      )}
                    </p>
                  )}
                  {!ent.resolved && ent.candidates && (
                    <div className="mt-1 ml-5 space-y-0.5">
                      {ent.candidates.map((c: string, j: number) => (
                        <p key={j} className="text-[var(--color-text-muted)] font-mono text-[10px]">
                          ? {c}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Schema Browser (collapsible) */}
        <div className="p-4">
          <button
            onClick={() => setSchemaOpen(!schemaOpen)}
            className="flex items-center gap-2 text-sm font-semibold text-[var(--color-text-muted)] uppercase tracking-wide w-full"
          >
            <Database size={14} />
            Schema Browser
            {schemaOpen ? <ChevronDown size={14} className="ml-auto" /> : <ChevronRight size={14} className="ml-auto" />}
          </button>
          {schemaOpen && (
            <div className="mt-3 space-y-1">
              {tables.map((t: any) => (
                <div key={t.table_name}>
                  <button
                    onClick={() => toggleTable(t.table_name)}
                    className="flex items-center gap-2 w-full text-left text-xs px-2 py-1.5 rounded hover:bg-[var(--color-bg-tertiary)] transition-colors"
                  >
                    {expandedTable === t.table_name ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                    <span className="font-mono">{t.table_name}</span>
                    {t.has_pii && <span className="text-[8px] px-1 py-0.5 bg-red-900/50 text-red-300 rounded">PII</span>}
                    <span className="ml-auto text-[var(--color-text-muted)]">{t.column_count} cols</span>
                  </button>
                  {expandedTable === t.table_name && tableDetails[t.table_name] && (
                    <div className="ml-6 mt-1 space-y-0.5">
                      {tableDetails[t.table_name].columns?.map((col: any) => (
                        <div key={col.name} className="flex items-center gap-2 text-[10px] px-2 py-1 rounded hover:bg-[var(--color-bg-tertiary)]">
                          <span className="font-mono text-[var(--color-text)]">{col.name}</span>
                          <span className="text-[var(--color-text-muted)]">{col.type}</span>
                          {col.is_pk && <span className="text-[8px] px-1 bg-blue-900/50 text-blue-300 rounded">PK</span>}
                          {col.is_pii && <span className="text-[8px] px-1 bg-red-900/50 text-red-300 rounded">PII</span>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}
