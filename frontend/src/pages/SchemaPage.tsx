import { useState, useEffect, useRef } from 'react';
import {
  Database, Key, Shield, ChevronDown, ChevronRight, ArrowRight, ArrowLeft,
  X, BookOpen, FlaskConical, GitBranch, ListChecks, BarChart3, Link2, Info,
  Pencil, Save, XCircle, Send, Sparkles, CalendarCheck, ShieldCheck,
  DollarSign, Users, LayoutDashboard, AlertTriangle, CheckCircle, AlertOctagon,
  Layers, History, Undo2, Trash2, ArrowLeftCircle
} from 'lucide-react';
import { api } from '../api';

const ICON_MAP: Record<string, any> = {
  CalendarCheck, BarChart3, ShieldCheck, DollarSign, Users, LayoutDashboard, Database,
};

// ── NL Message type ──
type NLMessage =
  | { role: 'user'; text: string }
  | { role: 'assistant'; text: string }
  | { role: 'proposal'; explanation: string; previews: any[]; impact: any[]; status: 'pending' | 'confirmed' | 'rejected' };

export function SchemaPage() {
  // App-level state
  const [apps, setApps] = useState<any[]>([]);
  const [selectedApp, setSelectedApp] = useState<any>(null);
  const [appDetail, setAppDetail] = useState<any>(null);
  const [appLoading, setAppLoading] = useState(false);

  // Table/column browsing (within selected app)
  const [expandedTable, setExpandedTable] = useState<string | null>(null);
  const [selectedColumn, setSelectedColumn] = useState<{ table: string; column: string } | null>(null);
  const [columnMeta, setColumnMeta] = useState<any>(null);
  const [metaLoading, setMetaLoading] = useState(false);

  // Inline editing
  const [editing, setEditing] = useState(false);
  const [editDraft, setEditDraft] = useState<any>(null);
  const [saving, setSaving] = useState(false);

  // Cross-app usage & impact analysis
  const [columnUsage, setColumnUsage] = useState<any[]>([]);
  const [impactResult, setImpactResult] = useState<any>(null);
  const [impactLoading, setImpactLoading] = useState(false);
  const [showImpactModal, setShowImpactModal] = useState(false);
  const [pendingSave, setPendingSave] = useState<Record<string, any> | null>(null);

  // Version history
  const [columnHistory, setColumnHistory] = useState<any[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [reverting, setReverting] = useState<number | null>(null);

  // Toast notification
  const [toast, setToast] = useState<string | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const showToast = (msg: string) => {
    setToast(msg);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 2500);
  };

  // NL command bar
  const [nlInput, setNlInput] = useState('');
  const [nlMessages, setNlMessages] = useState<NLMessage[]>([]);
  const [nlProcessing, setNlProcessing] = useState(false);
  const nlEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.listApplications().then((data: any) => {
      if (data.applications) setApps(data.applications);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    nlEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [nlMessages]);

  // ── App selection ──
  const selectApp = async (app: any) => {
    setSelectedApp(app);
    setAppDetail(null);
    setExpandedTable(null);
    setSelectedColumn(null);
    setColumnMeta(null);
    setEditing(false);
    setAppLoading(true);
    try {
      const detail = await api.getApplication(app.app_id);
      setAppDetail(detail);
    } catch {
      // ignore
    } finally {
      setAppLoading(false);
    }
  };

  const goBackToApps = () => {
    setSelectedApp(null);
    setAppDetail(null);
    setExpandedTable(null);
    setSelectedColumn(null);
    setColumnMeta(null);
    setEditing(false);
  };

  // ── Table toggle ──
  const toggleTable = (tableName: string) => {
    setExpandedTable(expandedTable === tableName ? null : tableName);
  };

  // ── Column selection ──
  const selectColumn = async (tableName: string, colName: string) => {
    const isSame = selectedColumn?.table === tableName && selectedColumn?.column === colName;
    if (isSame) {
      setSelectedColumn(null);
      setColumnMeta(null);
      setColumnUsage([]);
      setColumnHistory([]);
      setShowHistory(false);
      setEditing(false);
      return;
    }
    setSelectedColumn({ table: tableName, column: colName });
    setMetaLoading(true);
    setColumnMeta(null);
    setColumnUsage([]);
    setColumnHistory([]);
    setShowHistory(false);
    setEditing(false);
    setImpactResult(null);
    try {
      const [meta, usage, history] = await Promise.all([
        api.getColumnMetadata(tableName, colName),
        api.getColumnUsage(tableName, colName),
        api.getColumnHistory(tableName, colName),
      ]);
      setColumnMeta(meta);
      setColumnUsage(usage.applications || []);
      setColumnHistory(history.versions || []);
    } catch {
      setColumnMeta(null);
      setColumnUsage([]);
      setColumnHistory([]);
    } finally {
      setMetaLoading(false);
    }
  };

  const isColSelected = (table: string, col: string) =>
    selectedColumn?.table === table && selectedColumn?.column === col;

  // ── Inline editing helpers ──
  const startEditing = () => {
    if (!columnMeta) return;
    setEditDraft({
      business_name: columnMeta.business_name || '',
      business_description: columnMeta.business_description || '',
      valid_values: (columnMeta.valid_values || []).join(', '),
      sample_values: (columnMeta.sample_values || []).join(', '),
      formula: columnMeta.formula || '',
      business_rules: (columnMeta.business_rules || []).join('\n'),
      used_in_metrics: (columnMeta.used_in_metrics || []).join('\n'),
      relationships: (columnMeta.relationships || []).join('\n'),
      lineage_source: columnMeta.lineage?.source_system || '',
      lineage_frequency: columnMeta.lineage?.load_frequency || '',
      lineage_transformation: columnMeta.lineage?.transformation || '',
    });
    setEditing(true);
  };

  const cancelEditing = () => { setEditing(false); setEditDraft(null); setImpactResult(null); setShowImpactModal(false); setPendingSave(null); };

  const buildPayload = () => {
    if (!editDraft) return null;
    const splitList = (s: string) => s.trim() ? s.split('\n').map((x: string) => x.trim()).filter(Boolean) : [];
    const splitComma = (s: string) => s.trim() ? s.split(',').map((x: string) => x.trim()).filter(Boolean) : [];
    return {
      business_name: editDraft.business_name,
      business_description: editDraft.business_description,
      valid_values: splitComma(editDraft.valid_values),
      sample_values: splitComma(editDraft.sample_values),
      formula: editDraft.formula || null,
      business_rules: splitList(editDraft.business_rules),
      used_in_metrics: splitList(editDraft.used_in_metrics),
      relationships: splitList(editDraft.relationships),
      lineage: editDraft.lineage_source ? {
        source_system: editDraft.lineage_source,
        load_frequency: editDraft.lineage_frequency,
        transformation: editDraft.lineage_transformation,
      } : null,
    };
  };

  const saveEdits = async () => {
    if (!selectedColumn || !editDraft) return;
    const payload = buildPayload();
    if (!payload) return;

    // Check if other apps use this column — if so, run impact analysis first
    const otherApps = columnUsage.filter((a: any) => a.app_id !== selectedApp?.app_id);
    if (otherApps.length > 0 && !showImpactModal) {
      setImpactLoading(true);
      setImpactResult(null);
      setPendingSave(payload);
      try {
        const result = await api.getImpactAnalysis(
          selectedColumn.table, selectedColumn.column, payload, selectedApp?.app_id || ''
        );
        setImpactResult(result);
        setShowImpactModal(true);
      } catch {
        // If impact analysis fails, let user proceed anyway
        setImpactResult({ risk_level: 'warning', summary: 'Could not reach impact analysis service.', impacts: [], recommendations: ['Review changes manually.'] });
        setShowImpactModal(true);
      } finally {
        setImpactLoading(false);
      }
      return;
    }

    // Actually save
    setSaving(true);
    try {
      const updated = await api.updateColumnMetadata(selectedColumn.table, selectedColumn.column, payload);
      setColumnMeta(updated);
      setEditing(false);
      setEditDraft(null);
      setShowImpactModal(false);
      setImpactResult(null);
      setPendingSave(null);
      // Refresh history
      const hist = await api.getColumnHistory(selectedColumn.table, selectedColumn.column);
      setColumnHistory(hist.versions || []);
    } catch { /* keep editing */ } finally { setSaving(false); }
  };

  const confirmSaveAfterImpact = async () => {
    if (!selectedColumn || !pendingSave) return;
    setSaving(true);
    try {
      const updated = await api.updateColumnMetadata(selectedColumn.table, selectedColumn.column, pendingSave);
      setColumnMeta(updated);
      setEditing(false);
      setEditDraft(null);
      setShowImpactModal(false);
      setImpactResult(null);
      setPendingSave(null);
      // Refresh history
      const hist = await api.getColumnHistory(selectedColumn.table, selectedColumn.column);
      setColumnHistory(hist.versions || []);
    } catch { /* keep editing */ } finally { setSaving(false); }
  };

  const cancelImpact = () => {
    setShowImpactModal(false);
    setImpactResult(null);
    setPendingSave(null);
  };

  // ── Revert handler ──
  const handleRevert = async (historyId: number) => {
    if (!selectedColumn || reverting) return;
    setReverting(historyId);
    try {
      const updated = await api.revertChange(selectedColumn.table, selectedColumn.column, historyId);
      setColumnMeta(updated);
      // Refresh history
      const hist = await api.getColumnHistory(selectedColumn.table, selectedColumn.column);
      setColumnHistory(hist.versions || []);
      showToast('Change undone');
    } catch { /* ignore */ } finally {
      setReverting(null);
    }
  };

  // ── Delete version group ──
  const handleDeleteVersion = async (changeIds: number[]) => {
    if (!selectedColumn) return;
    try {
      const result = await api.deleteHistoryEntries(selectedColumn.table, selectedColumn.column, changeIds);
      setColumnHistory(result.versions || []);
    } catch { /* ignore */ }
  };

  const updateDraft = (field: string, value: string) => {
    setEditDraft((prev: any) => ({ ...prev, [field]: value }));
  };

  // ── NL command handler (preview first, then confirm) ──
  const handleNlSubmit = async () => {
    const instruction = nlInput.trim();
    if (!instruction || nlProcessing) return;
    setNlMessages((prev) => [...prev, { role: 'user', text: instruction }]);
    setNlInput('');
    setNlProcessing(true);
    try {
      const result = await api.nlPreview(instruction, selectedColumn ? { table_name: selectedColumn.table, column_name: selectedColumn.column } : undefined);
      if (result.error) {
        setNlMessages((prev) => [...prev, { role: 'assistant', text: result.error }]);
      } else if (result.preview_count === 0) {
        setNlMessages((prev) => [...prev, { role: 'assistant', text: result.explanation || 'No changes proposed.' }]);
      } else {
        setNlMessages((prev) => [...prev, { role: 'proposal', explanation: result.explanation, previews: result.previews, impact: result.impact || [], status: 'pending' }]);
      }
    } catch {
      setNlMessages((prev) => [...prev, { role: 'assistant', text: 'Something went wrong. Please try again.' }]);
    } finally {
      setNlProcessing(false);
    }
  };

  const handleNlConfirm = async (proposalIndex: number) => {
    const msg = nlMessages[proposalIndex];
    if (msg.role !== 'proposal' || msg.status !== 'pending') return;
    // Mark as confirmed
    setNlMessages((prev) => prev.map((m, i) => i === proposalIndex ? { ...m, status: 'confirmed' as const } : m));
    try {
      const result = await api.nlApply(msg.previews);
      const responseText = result.update_count > 0
        ? `Changes applied to ${result.update_count} column(s): ${result.applied.map((a: any) => `${a.table_name}.${a.column_name}`).join(', ')}`
        : 'No changes were applied.';
      setNlMessages((prev) => [...prev, { role: 'assistant', text: responseText }]);
      // Refresh selected column if affected
      if (selectedColumn && result.applied?.some((a: any) => a.table_name === selectedColumn.table && a.column_name === selectedColumn.column)) {
        const [meta, hist] = await Promise.all([
          api.getColumnMetadata(selectedColumn.table, selectedColumn.column),
          api.getColumnHistory(selectedColumn.table, selectedColumn.column),
        ]);
        setColumnMeta(meta);
        setColumnHistory(hist.versions || []);
      }
    } catch {
      setNlMessages((prev) => [...prev, { role: 'assistant', text: 'Failed to apply changes.' }]);
    }
  };

  const handleNlReject = (proposalIndex: number) => {
    setNlMessages((prev) => prev.map((m, i) => i === proposalIndex ? { ...m, status: 'rejected' as const } : m));
    setNlMessages((prev) => [...prev, { role: 'assistant', text: 'Changes discarded.' }]);
  };

  // ── RENDER ──
  return (
    <div className="flex flex-col h-screen">
      {/* Toast notification */}
      {toast && (
        <div className="fixed top-6 left-1/2 -translate-x-1/2 z-50 bg-green-600 text-white px-5 py-2.5 rounded-lg shadow-lg text-sm font-medium flex items-center gap-2 animate-fade-in">
          <CheckCircle className="w-4 h-4" /> {toast}
        </div>
      )}
      {/* Main content area */}
      <div className="flex flex-1 min-h-0 gap-0">
        {/* ── Left Panel ── */}
        <div className={`${selectedColumn ? 'w-1/2' : 'w-full'} transition-all duration-300 flex flex-col min-h-0 border-r border-[var(--color-border)]`}>
          <div className="flex-1 overflow-y-auto p-4">
            {!selectedApp ? (
              /* ── APPLICATION CARDS VIEW ── */
              <>
                <div className="mb-6">
                  <h1 className="text-2xl font-bold flex items-center gap-3">
                    <Database size={24} className="text-[var(--color-primary)]" />
                    Semantic Bridge
                  </h1>
                  <p className="text-[var(--color-text-muted)] mt-1 text-sm">
                    Select an application to explore its schema. Use the command bar below for natural language updates.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {apps.map((app: any) => {
                    const IconComp = ICON_MAP[app.icon] || Database;
                    return (
                      <button
                        key={app.app_id}
                        onClick={() => selectApp(app)}
                        className="text-left p-5 bg-[var(--color-bg-secondary)] rounded-xl border border-[var(--color-border)] hover:border-[var(--color-primary)] hover:bg-[var(--color-bg-tertiary)] transition-all group"
                      >
                        <div className="flex items-start gap-4">
                          <div className="w-10 h-10 rounded-lg bg-[var(--color-primary)]/20 flex items-center justify-center shrink-0 group-hover:bg-[var(--color-primary)]/30 transition-colors">
                            <IconComp size={20} className="text-[var(--color-primary-light)]" />
                          </div>
                          <div className="min-w-0">
                            <h3 className="font-semibold text-sm">{app.app_name}</h3>
                            <p className="text-xs text-[var(--color-text-muted)] mt-1 line-clamp-2">{app.description}</p>
                            <div className="flex gap-3 mt-3 text-[10px] text-[var(--color-text-muted)]">
                              <span>{app.table_count} tables</span>
                              <span>{app.column_count} columns</span>
                            </div>
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </>
            ) : (
              /* ── TABLE BROWSER within selected app ── */
              <>
                <div className="mb-4">
                  <button
                    onClick={goBackToApps}
                    className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors mb-3"
                  >
                    <ArrowLeft size={14} /> All Applications
                  </button>
                  <h1 className="text-xl font-bold flex items-center gap-3">
                    {(() => { const IC = ICON_MAP[selectedApp.icon] || Database; return <IC size={22} className="text-[var(--color-primary)]" />; })()}
                    {selectedApp.app_name}
                  </h1>
                  <p className="text-[var(--color-text-muted)] mt-1 text-sm">{selectedApp.description}</p>
                </div>

                {appLoading ? (
                  <div className="p-8 text-center text-[var(--color-text-muted)]">Loading schema...</div>
                ) : appDetail ? (
                  <div className="space-y-2">
                    {appDetail.tables.map((t: any) => (
                      <div
                        key={t.table_name}
                        className="bg-[var(--color-bg-secondary)] rounded-xl border border-[var(--color-border)] overflow-hidden"
                      >
                        <button
                          onClick={() => toggleTable(t.table_name)}
                          className="w-full text-left px-4 py-3 flex items-center gap-3 hover:bg-[var(--color-bg-tertiary)] transition-colors"
                        >
                          {expandedTable === t.table_name ? (
                            <ChevronDown size={16} className="text-[var(--color-text-muted)]" />
                          ) : (
                            <ChevronRight size={16} className="text-[var(--color-text-muted)]" />
                          )}
                          <span className="font-mono text-sm font-medium">{t.table_name}</span>
                          <span className="text-xs text-[var(--color-text-muted)] hidden sm:inline">{t.description}</span>
                          <div className="ml-auto flex items-center gap-2 shrink-0">
                            {t.has_pii && (
                              <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 bg-red-900/50 text-red-300 rounded-full border border-red-800">
                                <Shield size={10} /> PII
                              </span>
                            )}
                            <span className="text-xs text-[var(--color-text-muted)]">{t.column_count} cols</span>
                          </div>
                        </button>

                        {expandedTable === t.table_name && (
                          <div className="border-t border-[var(--color-border)]">
                            {t.columns.map((col: any) => {
                              const selected = isColSelected(t.table_name, col.name);
                              return (
                                <button
                                  key={col.name}
                                  onClick={() => selectColumn(t.table_name, col.name)}
                                  className={`w-full text-left px-4 py-2.5 flex items-center gap-3 text-xs border-t border-[var(--color-border)] transition-colors cursor-pointer ${
                                    selected
                                      ? 'bg-[var(--color-primary)]/10 border-l-2 border-l-[var(--color-primary)]'
                                      : 'hover:bg-[var(--color-bg-tertiary)]'
                                  }`}
                                >
                                  <div className={`w-3 h-3 rounded-sm border flex items-center justify-center shrink-0 ${
                                    selected ? 'bg-[var(--color-primary)] border-[var(--color-primary)]' : 'border-[var(--color-border)]'
                                  }`}>
                                    {selected && (
                                      <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
                                        <path d="M1.5 4L3 5.5L6.5 2" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                                      </svg>
                                    )}
                                  </div>
                                  <span className="font-mono w-40 shrink-0">{col.name}</span>
                                  <span className="text-[var(--color-text-muted)] w-20 shrink-0">{col.type}</span>
                                  <span className="text-[var(--color-text-muted)] flex-1 truncate">{col.description}</span>
                                  <div className="flex gap-1 shrink-0">
                                    {col.is_pk && (
                                      <span className="flex items-center gap-0.5 px-1.5 py-0.5 bg-blue-900/50 text-blue-300 rounded text-[10px] border border-blue-800">
                                        <Key size={8} /> PK
                                      </span>
                                    )}
                                    {col.is_pii && (
                                      <span className="flex items-center gap-0.5 px-1.5 py-0.5 bg-red-900/50 text-red-300 rounded text-[10px] border border-red-800">
                                        <Shield size={8} /> PII
                                      </span>
                                    )}
                                  </div>
                                </button>
                              );
                            })}

                            {t.foreign_keys?.length > 0 && (
                              <div className="px-4 py-3 border-t border-[var(--color-border)] bg-[var(--color-bg-tertiary)]">
                                <p className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wide mb-1.5">Foreign Keys</p>
                                <div className="space-y-1">
                                  {t.foreign_keys.map((fk: any, i: number) => (
                                    <div key={i} className="flex items-center gap-2 text-xs text-[var(--color-text-muted)]">
                                      <span className="font-mono">{fk.column}</span>
                                      <ArrowRight size={10} />
                                      <span className="font-mono text-[var(--color-primary-light)]">{fk.references}</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : null}
              </>
            )}
          </div>

          {/* ── NL Command Bar (always visible at bottom) ── */}
          <div className="border-t border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
            {/* NL message history */}
            {nlMessages.length > 0 && (
              <div className="max-h-96 overflow-y-auto px-4 pt-3 space-y-3">
                {nlMessages.map((msg, i) => {
                  if (msg.role === 'user') {
                    return (
                      <div key={i} className="flex gap-2 items-start">
                        <span className="shrink-0 w-6 h-6 rounded-full bg-blue-600/30 flex items-center justify-center text-[10px] font-bold text-blue-300 mt-0.5">U</span>
                        <p className="text-xs leading-relaxed text-[var(--color-text)] whitespace-pre-wrap">{msg.text}</p>
                      </div>
                    );
                  }
                  if (msg.role === 'assistant') {
                    return (
                      <div key={i} className="flex gap-2 items-start">
                        <span className="shrink-0 w-6 h-6 rounded-full bg-purple-600/30 flex items-center justify-center text-[10px] font-bold text-purple-300 mt-0.5">AI</span>
                        <p className="text-xs leading-relaxed text-[var(--color-primary-light)] whitespace-pre-wrap">{msg.text}</p>
                      </div>
                    );
                  }
                  if (msg.role === 'proposal') {
                    const riskColor = (level: string) => level === 'critical' ? 'text-red-400 bg-red-900/30 border-red-700/40' : level === 'warning' ? 'text-amber-400 bg-amber-900/30 border-amber-700/40' : 'text-emerald-400 bg-emerald-900/30 border-emerald-700/40';
                    return (
                      <div key={i} className="flex gap-2 items-start">
                        <span className="shrink-0 w-6 h-6 rounded-full bg-purple-600/30 flex items-center justify-center text-[10px] font-bold text-purple-300 mt-0.5">AI</span>
                        <div className="flex-1 space-y-2">
                          <p className="text-xs text-[var(--color-primary-light)]">{msg.explanation}</p>
                          {/* Proposed field changes */}
                          {msg.previews.map((prev: any, pi: number) => (
                            <div key={pi} className="bg-[var(--color-bg-tertiary)] rounded-lg border border-[var(--color-border)] p-2.5">
                              <p className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wide mb-2">
                                Proposed changes for <span className="font-mono text-[var(--color-primary-light)]">{prev.table_name}.{prev.column_name}</span>
                              </p>
                              <div className="space-y-1.5">
                                {prev.diffs.map((d: any, di: number) => (
                                  <div key={di} className="text-[11px]">
                                    <span className="font-mono font-semibold text-[var(--color-text)]">{d.field}</span>
                                    <div className="grid grid-cols-2 gap-2 mt-0.5">
                                      <div className="bg-[var(--color-bg)] rounded p-1.5 border border-[var(--color-border)]">
                                        <pre className="whitespace-pre-wrap font-mono text-[10px] text-red-300/80">{d.old_value != null ? (typeof d.old_value === 'object' ? JSON.stringify(d.old_value, null, 2) : String(d.old_value)) : '(empty)'}</pre>
                                      </div>
                                      <div className="bg-[var(--color-bg)] rounded p-1.5 border border-emerald-800/30">
                                        <pre className="whitespace-pre-wrap font-mono text-[10px] text-emerald-300/80">{d.new_value != null ? (typeof d.new_value === 'object' ? JSON.stringify(d.new_value, null, 2) : String(d.new_value)) : '(empty)'}</pre>
                                      </div>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ))}
                          {/* Impact analysis */}
                          {msg.impact.length > 0 && msg.impact.some((imp: any) => imp.risk_level !== 'safe') && (
                            <div className="space-y-1.5">
                              {msg.impact.filter((imp: any) => imp.risk_level !== 'safe').map((imp: any, ii: number) => (
                                <div key={ii} className={`rounded-lg border p-2.5 ${riskColor(imp.risk_level)}`}>
                                  <div className="flex items-center gap-2 mb-1">
                                    <AlertTriangle size={12} />
                                    <span className="text-[10px] font-bold uppercase">{imp.risk_level} Impact</span>
                                    <span className="text-[10px] opacity-70">{imp.table_name}.{imp.column_name}</span>
                                  </div>
                                  <p className="text-[11px] mb-1">{imp.summary}</p>
                                  {imp.impacts?.length > 0 && (
                                    <ul className="text-[10px] space-y-0.5 opacity-80 ml-3">
                                      {imp.impacts.map((detail: any, di: number) => (
                                        <li key={di} className="list-disc">{detail.app_name}: {detail.concern}</li>
                                      ))}
                                    </ul>
                                  )}
                                  {imp.recommendations?.length > 0 && (
                                    <div className="mt-1.5 text-[10px] opacity-80">
                                      <span className="font-semibold">Recommendations: </span>
                                      {imp.recommendations.join('; ')}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                          {msg.impact.length > 0 && msg.impact.every((imp: any) => imp.risk_level === 'safe') && (
                            <div className="flex items-center gap-2 text-[11px] text-emerald-400">
                              <CheckCircle size={12} /> No cross-application impact detected.
                            </div>
                          )}
                          {/* Confirm / Reject buttons */}
                          {msg.status === 'pending' ? (
                            <div className="flex gap-2 pt-1">
                              <button onClick={() => handleNlConfirm(i)} className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-emerald-600/80 text-white rounded-lg hover:bg-emerald-600 transition-colors">
                                <CheckCircle size={12} /> Confirm &amp; Apply
                              </button>
                              <button onClick={() => handleNlReject(i)} className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-[var(--color-bg)] text-[var(--color-text-muted)] rounded-lg border border-[var(--color-border)] hover:bg-[var(--color-bg-tertiary)] transition-colors">
                                <XCircle size={12} /> Discard
                              </button>
                            </div>
                          ) : (
                            <p className={`text-[10px] italic ${msg.status === 'confirmed' ? 'text-emerald-400' : 'text-[var(--color-text-muted)]'}`}>
                              {msg.status === 'confirmed' ? '✓ Changes applied' : '✗ Changes discarded'}
                            </p>
                          )}
                        </div>
                      </div>
                    );
                  }
                  return null;
                })}
                <div ref={nlEndRef} />
              </div>
            )}
            <div className="p-3 flex gap-2">
              <div className="relative flex-1">
                <Sparkles size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-primary-light)]" />
                <input
                  type="text"
                  value={nlInput}
                  onChange={(e) => setNlInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleNlSubmit()}
                  placeholder="Describe a metadata update in natural language..."
                  disabled={nlProcessing}
                  className="w-full pl-9 pr-3 py-2.5 text-sm bg-[var(--color-bg)] border border-[var(--color-border)] rounded-lg text-[var(--color-text)] placeholder:text-[var(--color-text-muted)]/50 focus:outline-none focus:ring-1 focus:ring-[var(--color-primary)] disabled:opacity-50"
                />
              </div>
              <button
                onClick={handleNlSubmit}
                disabled={!nlInput.trim() || nlProcessing}
                className="px-3 py-2 bg-[var(--color-primary)] text-white rounded-lg hover:bg-[var(--color-primary-dark)] disabled:opacity-50 transition-colors shrink-0"
              >
                {nlProcessing ? (
                  <span className="w-4 h-4 block border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <Send size={16} />
                )}
              </button>
            </div>
          </div>
        </div>

        {/* ── Right Panel: Column Detail ── */}
        {selectedColumn && (
          <div className="w-1/2 bg-[var(--color-bg-secondary)] flex flex-col min-h-0 relative">
            {/* Header */}
            <div className="bg-[var(--color-bg-secondary)] border-b border-[var(--color-border)] p-4 flex items-start justify-between shrink-0">
              <div>
                <p className="text-[10px] uppercase tracking-wide text-[var(--color-text-muted)] mb-1">Column Detail</p>
                <h2 className="text-lg font-bold font-mono">
                  <span className="text-[var(--color-text-muted)]">{selectedColumn.table}.</span>{selectedColumn.column}
                </h2>
                {columnMeta?.business_name && !editing && (
                  <p className="text-sm text-[var(--color-primary-light)] mt-0.5">{columnMeta.business_name}</p>
                )}
              </div>
              <div className="flex items-center gap-2">
                {!editing && columnMeta && (
                  <>
                    <button onClick={() => setShowHistory(!showHistory)} className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg transition-colors ${showHistory ? 'bg-amber-600/20 text-amber-300' : 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-muted)] hover:bg-[var(--color-bg)]'}`}>
                      <History size={12} /> {columnHistory.length > 0 ? `History (${columnHistory.length})` : 'History'}
                    </button>
                    <button onClick={startEditing} className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-[var(--color-primary)]/20 text-[var(--color-primary-light)] rounded-lg hover:bg-[var(--color-primary)]/30 transition-colors">
                      <Pencil size={12} /> Edit
                    </button>
                  </>
                )}
                {editing && (
                  <>
                    <button onClick={saveEdits} disabled={saving || impactLoading} className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-emerald-600/80 text-white rounded-lg hover:bg-emerald-600 transition-colors disabled:opacity-50">
                      <Save size={12} /> {impactLoading ? 'Analyzing...' : saving ? 'Saving...' : 'Save'}
                    </button>
                    <button onClick={cancelEditing} className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-[var(--color-bg-tertiary)] text-[var(--color-text-muted)] rounded-lg hover:bg-[var(--color-bg)] transition-colors">
                      <XCircle size={12} /> Cancel
                    </button>
                  </>
                )}
                <button onClick={() => { setSelectedColumn(null); setColumnMeta(null); setColumnUsage([]); setColumnHistory([]); setShowHistory(false); setEditing(false); setEditDraft(null); setImpactResult(null); setShowImpactModal(false); }} className="p-1 hover:bg-[var(--color-bg-tertiary)] rounded-lg transition-colors">
                  <X size={18} className="text-[var(--color-text-muted)]" />
                </button>
              </div>
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto">
              {metaLoading ? (
                <div className="p-8 text-center text-[var(--color-text-muted)]">Loading...</div>
              ) : showHistory ? (
                /* ── VERSION HISTORY VIEW ── */
                <div className="p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)] flex items-center gap-2">
                      <History size={14} className="text-amber-400" /> Change History
                    </h3>
                    <button
                      onClick={() => setShowHistory(false)}
                      className="flex items-center gap-1.5 px-2.5 py-1 text-[10px] bg-[var(--color-primary)]/20 text-[var(--color-primary-light)] rounded-lg hover:bg-[var(--color-primary)]/30 transition-colors"
                    >
                      <ArrowLeftCircle size={12} /> Back to Metadata
                    </button>
                  </div>
                  {columnHistory.length === 0 ? (
                    <p className="text-sm text-[var(--color-text-muted)] text-center py-8">No changes recorded yet.</p>
                  ) : (
                    <div className="space-y-4">
                      {columnHistory.map((ver: any) => {
                        const date = new Date(ver.timestamp * 1000);
                        const timeStr = date.toLocaleString();
                        const sourceLabel = ver.source === 'nl-update' ? 'NL Update' : ver.source === 'manual' ? 'Manual Edit' : 'Revert';
                        const sourceColor = ver.source === 'nl-update' ? 'text-purple-300 bg-purple-900/20 border-purple-800/30' : ver.source === 'manual' ? 'text-blue-300 bg-blue-900/20 border-blue-800/30' : 'text-amber-300 bg-amber-900/20 border-amber-800/30';
                        const allIds = ver.changes.map((c: any) => c.id);
                        return (
                          <div key={ver.version} className="bg-[var(--color-bg-tertiary)] rounded-lg border border-[var(--color-border)] overflow-hidden">
                            {/* Version header */}
                            <div className="flex items-center justify-between px-3 py-2 bg-[var(--color-bg)]/50 border-b border-[var(--color-border)]">
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-bold text-[var(--color-primary-light)]">Version {ver.version}</span>
                                <span className={`px-1.5 py-0.5 rounded text-[10px] border ${sourceColor}`}>{sourceLabel}</span>
                                <span className="text-[10px] text-[var(--color-text-muted)]">{timeStr}</span>
                                <span className="text-[10px] text-[var(--color-text-muted)]">&middot; {ver.changes.length} field{ver.changes.length !== 1 ? 's' : ''}</span>
                              </div>
                              <div className="flex items-center gap-1">
                                {ver.source !== 'revert' && ver.changes.length === 1 && (
                                  <button
                                    onClick={() => handleRevert(ver.changes[0].id)}
                                    disabled={reverting === ver.changes[0].id}
                                    className="flex items-center gap-1 px-2 py-1 text-[10px] bg-amber-600/20 text-amber-300 rounded hover:bg-amber-600/30 transition-colors disabled:opacity-50"
                                  >
                                    <Undo2 size={10} /> {reverting === ver.changes[0].id ? 'Reverting...' : 'Undo'}
                                  </button>
                                )}
                                <button
                                  onClick={() => handleDeleteVersion(allIds)}
                                  className="flex items-center gap-1 px-2 py-1 text-[10px] bg-red-600/20 text-red-300 rounded hover:bg-red-600/30 transition-colors"
                                >
                                  <Trash2 size={10} /> Delete
                                </button>
                              </div>
                            </div>
                            {/* Field changes */}
                            <div className="p-3 space-y-2">
                              {ver.changes.map((h: any) => (
                                <div key={h.id}>
                                  <p className="text-xs font-medium mb-1">
                                    <span className="text-[var(--color-text-muted)]">Field:</span> <span className="font-mono">{h.field}</span>
                                    {ver.source !== 'revert' && ver.changes.length > 1 && (
                                      <button
                                        onClick={() => handleRevert(h.id)}
                                        disabled={reverting === h.id}
                                        className="ml-2 inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[9px] bg-amber-600/20 text-amber-300 rounded hover:bg-amber-600/30 transition-colors disabled:opacity-50"
                                      >
                                        <Undo2 size={8} /> {reverting === h.id ? '...' : 'Undo'}
                                      </button>
                                    )}
                                  </p>
                                  <div className="grid grid-cols-2 gap-2 text-[11px]">
                                    <div>
                                      <p className="text-[var(--color-text-muted)] mb-0.5">Previous</p>
                                      <div className="bg-[var(--color-bg)] rounded p-2 border border-[var(--color-border)] max-h-24 overflow-y-auto">
                                        <pre className="whitespace-pre-wrap font-mono text-red-300/80">{h.old_value != null ? (typeof h.old_value === 'object' ? JSON.stringify(h.old_value, null, 2) : String(h.old_value)) : '(empty)'}</pre>
                                      </div>
                                    </div>
                                    <div>
                                      <p className="text-[var(--color-text-muted)] mb-0.5">Updated to</p>
                                      <div className="bg-[var(--color-bg)] rounded p-2 border border-[var(--color-border)] max-h-24 overflow-y-auto">
                                        <pre className="whitespace-pre-wrap font-mono text-emerald-300/80">{h.new_value != null ? (typeof h.new_value === 'object' ? JSON.stringify(h.new_value, null, 2) : String(h.new_value)) : '(empty)'}</pre>
                                      </div>
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              ) : columnMeta && editing && editDraft ? (
                <div className="p-4 space-y-5">
                  <EditField label="Business Name" value={editDraft.business_name} onChange={(v) => updateDraft('business_name', v)} />
                  <EditField label="Business Description" value={editDraft.business_description} onChange={(v) => updateDraft('business_description', v)} multiline rows={3} />
                  <EditField label="Valid Values (comma-separated)" value={editDraft.valid_values} onChange={(v) => updateDraft('valid_values', v)} placeholder="e.g. US, CA, GB" />
                  <EditField label="Sample Values (comma-separated)" value={editDraft.sample_values} onChange={(v) => updateDraft('sample_values', v)} placeholder="e.g. 2025-01-01, 2024-06-15" />
                  <EditField label="Formula / Derivation" value={editDraft.formula} onChange={(v) => updateDraft('formula', v)} multiline rows={2} />
                  <EditField label="Business Rules (one per line)" value={editDraft.business_rules} onChange={(v) => updateDraft('business_rules', v)} multiline rows={4} />
                  <EditField label="Used in Metrics (one per line)" value={editDraft.used_in_metrics} onChange={(v) => updateDraft('used_in_metrics', v)} multiline rows={3} />
                  <EditField label="Relationships (one per line)" value={editDraft.relationships} onChange={(v) => updateDraft('relationships', v)} multiline rows={3} />
                  <div className="border-t border-[var(--color-border)] pt-4">
                    <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)] mb-3 flex items-center gap-2">
                      <GitBranch size={14} className="text-[var(--color-primary-light)]" /> Data Lineage
                    </h3>
                    <div className="space-y-3 ml-5">
                      <EditField label="Source System" value={editDraft.lineage_source} onChange={(v) => updateDraft('lineage_source', v)} />
                      <EditField label="Load Frequency" value={editDraft.lineage_frequency} onChange={(v) => updateDraft('lineage_frequency', v)} />
                      <EditField label="Transformation" value={editDraft.lineage_transformation} onChange={(v) => updateDraft('lineage_transformation', v)} multiline rows={2} />
                    </div>
                  </div>

                  {/* Cross-app warning banner in edit mode */}
                  {(() => {
                    const otherApps = columnUsage.filter((a: any) => a.app_id !== selectedApp?.app_id);
                    if (otherApps.length === 0) return null;
                    return (
                      <div className="border border-amber-800/50 bg-amber-900/10 rounded-lg p-3">
                        <div className="flex items-center gap-2 mb-2">
                          <AlertTriangle size={14} className="text-amber-400 shrink-0" />
                          <span className="text-xs font-medium text-amber-300">
                            {otherApps.length} other app{otherApps.length > 1 ? 's' : ''} also use{otherApps.length === 1 ? 's' : ''} this column
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-1.5 ml-5">
                          {otherApps.map((app: any) => (
                            <span key={app.app_id} className="px-2 py-0.5 bg-amber-900/20 text-amber-300/80 rounded text-[10px] border border-amber-800/30">
                              {app.app_name}
                            </span>
                          ))}
                        </div>
                        <p className="text-[10px] text-[var(--color-text-muted)] mt-2 ml-5">
                          AI will analyze impact on these apps when you save.
                        </p>
                      </div>
                    );
                  })()}
                </div>
              ) : columnMeta ? (
                <div className="p-4 space-y-5">
                  {columnMeta.business_description && (
                    <DetailSection icon={<BookOpen size={14} />} title="Business Description">
                      <p className="text-sm leading-relaxed">{columnMeta.business_description}</p>
                    </DetailSection>
                  )}
                  {columnMeta.valid_values && columnMeta.valid_values.length > 0 && (
                    <DetailSection icon={<ListChecks size={14} />} title="Valid Values">
                      <div className="flex flex-wrap gap-1.5">
                        {columnMeta.valid_values.map((v: string) => (
                          <span key={v} className="px-2 py-1 bg-[var(--color-bg-tertiary)] rounded-md text-xs font-mono border border-[var(--color-border)]">{v}</span>
                        ))}
                      </div>
                    </DetailSection>
                  )}
                  {columnMeta.sample_values && columnMeta.sample_values.length > 0 && (
                    <DetailSection icon={<FlaskConical size={14} />} title="Sample Values">
                      <div className="flex flex-wrap gap-1.5">
                        {columnMeta.sample_values.map((v: string, i: number) => (
                          <span key={i} className="px-2 py-1 bg-indigo-900/30 rounded-md text-xs font-mono text-indigo-300 border border-indigo-800/50">{v}</span>
                        ))}
                      </div>
                    </DetailSection>
                  )}
                  {columnMeta.formula && (
                    <DetailSection icon={<BarChart3 size={14} />} title="Formula / Derivation">
                      <div className="bg-[var(--color-bg)] rounded-lg p-3 border border-[var(--color-border)]">
                        <code className="text-xs text-emerald-300 font-mono whitespace-pre-wrap leading-relaxed">{columnMeta.formula}</code>
                      </div>
                    </DetailSection>
                  )}
                  {columnMeta.business_rules && columnMeta.business_rules.length > 0 && (
                    <DetailSection icon={<Info size={14} />} title="Business Rules">
                      <ul className="space-y-2">
                        {columnMeta.business_rules.map((rule: string, i: number) => (
                          <li key={i} className="flex gap-2 text-sm"><span className="text-[var(--color-primary)] mt-0.5 shrink-0">&#8226;</span><span className="leading-relaxed">{rule}</span></li>
                        ))}
                      </ul>
                    </DetailSection>
                  )}
                  {columnMeta.lineage && (
                    <DetailSection icon={<GitBranch size={14} />} title="Data Lineage">
                      <div className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
                        <span className="text-[var(--color-text-muted)]">Source System</span><span>{columnMeta.lineage.source_system}</span>
                        <span className="text-[var(--color-text-muted)]">Load Frequency</span><span>{columnMeta.lineage.load_frequency}</span>
                        <span className="text-[var(--color-text-muted)]">Transformation</span><span className="leading-relaxed">{columnMeta.lineage.transformation}</span>
                      </div>
                    </DetailSection>
                  )}
                  {columnMeta.used_in_metrics && columnMeta.used_in_metrics.length > 0 && (
                    <DetailSection icon={<BarChart3 size={14} />} title="Used in Metrics">
                      <ul className="space-y-1.5">
                        {columnMeta.used_in_metrics.map((m: string, i: number) => (
                          <li key={i} className="text-sm flex gap-2"><span className="text-amber-400 shrink-0">&rarr;</span><span>{m}</span></li>
                        ))}
                      </ul>
                    </DetailSection>
                  )}
                  {columnMeta.relationships && columnMeta.relationships.length > 0 && (
                    <DetailSection icon={<Link2 size={14} />} title="Relationships">
                      <ul className="space-y-1.5">
                        {columnMeta.relationships.map((r: string, i: number) => (
                          <li key={i} className="text-sm flex gap-2"><span className="text-[var(--color-primary-light)] shrink-0">&harr;</span><span>{r}</span></li>
                        ))}
                      </ul>
                    </DetailSection>
                  )}

                  {/* ── Used by Applications ── */}
                  {columnUsage.length > 0 && (
                    <DetailSection icon={<Layers size={14} />} title={`Used by ${columnUsage.length} Application${columnUsage.length > 1 ? 's' : ''}`}>
                      <div className="space-y-2">
                        {columnUsage.map((app: any) => {
                          const isCurrentApp = app.app_id === selectedApp?.app_id;
                          const AppIcon = ICON_MAP[app.icon] || Database;
                          return (
                            <div
                              key={app.app_id}
                              className={`flex items-center gap-3 p-2.5 rounded-lg border text-xs ${
                                isCurrentApp
                                  ? 'bg-[var(--color-primary)]/10 border-[var(--color-primary)]/30'
                                  : 'bg-[var(--color-bg-tertiary)] border-[var(--color-border)]'
                              }`}
                            >
                              <AppIcon size={16} className={isCurrentApp ? 'text-[var(--color-primary-light)]' : 'text-[var(--color-text-muted)]'} />
                              <div className="min-w-0 flex-1">
                                <span className={`font-medium ${isCurrentApp ? 'text-[var(--color-primary-light)]' : ''}`}>
                                  {app.app_name}
                                </span>
                                {isCurrentApp && (
                                  <span className="ml-2 text-[10px] px-1.5 py-0.5 bg-[var(--color-primary)]/20 text-[var(--color-primary-light)] rounded">current</span>
                                )}
                              </div>
                            </div>
                          );
                        })}
                        {columnUsage.filter((a: any) => a.app_id !== selectedApp?.app_id).length > 0 && (
                          <p className="text-[10px] text-amber-400/80 flex items-center gap-1.5 mt-1">
                            <AlertTriangle size={10} />
                            Changes to this column may affect other applications
                          </p>
                        )}
                      </div>
                    </DetailSection>
                  )}
                </div>
              ) : (
                <div className="p-8 text-center text-[var(--color-text-muted)]">No metadata available</div>
              )}
            </div>

            {/* ── Impact Analysis Loading Overlay ── */}
            {impactLoading && (
              <div className="absolute inset-0 bg-black/40 flex items-center justify-center z-10 rounded-lg">
                <div className="bg-[var(--color-bg-secondary)] rounded-xl p-6 text-center border border-[var(--color-border)] shadow-xl max-w-sm">
                  <span className="w-8 h-8 block mx-auto mb-3 border-3 border-[var(--color-primary)]/30 border-t-[var(--color-primary)] rounded-full animate-spin" />
                  <p className="text-sm font-medium">Analyzing cross-app impact...</p>
                  <p className="text-xs text-[var(--color-text-muted)] mt-1">Checking how this change affects other applications</p>
                </div>
              </div>
            )}

            {/* ── Impact Analysis Modal ── */}
            {showImpactModal && impactResult && (
              <div className="absolute inset-0 bg-black/50 flex items-center justify-center z-20 p-4">
                <div className="bg-[var(--color-bg-secondary)] rounded-xl border border-[var(--color-border)] shadow-2xl max-w-md w-full max-h-[80vh] flex flex-col">
                  {/* Modal Header */}
                  <div className={`p-4 border-b border-[var(--color-border)] flex items-center gap-3 shrink-0 ${
                    impactResult.risk_level === 'critical' ? 'bg-red-900/20' :
                    impactResult.risk_level === 'warning' ? 'bg-amber-900/20' :
                    'bg-emerald-900/20'
                  }`}>
                    {impactResult.risk_level === 'critical' ? (
                      <AlertOctagon size={20} className="text-red-400 shrink-0" />
                    ) : impactResult.risk_level === 'warning' ? (
                      <AlertTriangle size={20} className="text-amber-400 shrink-0" />
                    ) : (
                      <CheckCircle size={20} className="text-emerald-400 shrink-0" />
                    )}
                    <div>
                      <h3 className="font-semibold text-sm">
                        {impactResult.risk_level === 'critical' ? 'Critical Impact Detected' :
                         impactResult.risk_level === 'warning' ? 'Potential Impact Warning' :
                         'Safe to Update'}
                      </h3>
                      <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{impactResult.summary}</p>
                    </div>
                  </div>

                  {/* Modal Body */}
                  <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {/* Impacts */}
                    {impactResult.impacts && impactResult.impacts.length > 0 && (
                      <div>
                        <h4 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)] mb-2">Affected Applications</h4>
                        <div className="space-y-2">
                          {impactResult.impacts.map((impact: any, i: number) => (
                            <div key={i} className={`p-3 rounded-lg border text-xs ${
                              impact.severity === 'high' ? 'bg-red-900/10 border-red-800/50' :
                              impact.severity === 'medium' ? 'bg-amber-900/10 border-amber-800/50' :
                              'bg-[var(--color-bg-tertiary)] border-[var(--color-border)]'
                            }`}>
                              <div className="flex items-center gap-2 mb-1">
                                <span className={`font-medium ${
                                  impact.severity === 'high' ? 'text-red-300' :
                                  impact.severity === 'medium' ? 'text-amber-300' : ''
                                }`}>{impact.app_name}</span>
                                <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                                  impact.severity === 'high' ? 'bg-red-900/30 text-red-300' :
                                  impact.severity === 'medium' ? 'bg-amber-900/30 text-amber-300' :
                                  'bg-[var(--color-bg)] text-[var(--color-text-muted)]'
                                }`}>{impact.severity}</span>
                              </div>
                              <p className="text-[var(--color-text-muted)] leading-relaxed">{impact.concern}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Recommendations */}
                    {impactResult.recommendations && impactResult.recommendations.length > 0 && (
                      <div>
                        <h4 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)] mb-2">Recommendations</h4>
                        <ul className="space-y-1.5">
                          {impactResult.recommendations.map((rec: string, i: number) => (
                            <li key={i} className="text-xs flex gap-2 leading-relaxed">
                              <span className="text-[var(--color-primary-light)] shrink-0 mt-0.5">&rarr;</span>
                              <span>{rec}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  {/* Modal Footer */}
                  <div className="p-4 border-t border-[var(--color-border)] flex gap-2 justify-end shrink-0">
                    <button
                      onClick={cancelImpact}
                      className="px-4 py-2 text-xs bg-[var(--color-bg-tertiary)] text-[var(--color-text-muted)] rounded-lg hover:bg-[var(--color-bg)] transition-colors"
                    >
                      Go Back
                    </button>
                    <button
                      onClick={confirmSaveAfterImpact}
                      disabled={saving}
                      className={`px-4 py-2 text-xs text-white rounded-lg transition-colors disabled:opacity-50 ${
                        impactResult.risk_level === 'critical'
                          ? 'bg-red-600 hover:bg-red-700'
                          : 'bg-emerald-600 hover:bg-emerald-700'
                      }`}
                    >
                      {saving ? 'Saving...' : impactResult.risk_level === 'critical' ? 'Save Anyway' : 'Confirm & Save'}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}


function DetailSection({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-[var(--color-primary-light)]">{icon}</span>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">{title}</h3>
      </div>
      <div className="ml-5">{children}</div>
    </div>
  );
}

function EditField({ label, value, onChange, multiline, rows, placeholder }: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  multiline?: boolean;
  rows?: number;
  placeholder?: string;
}) {
  const cls = "w-full bg-[var(--color-bg)] border border-[var(--color-border)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:ring-1 focus:ring-[var(--color-primary)] placeholder:text-[var(--color-text-muted)]/50";
  return (
    <div>
      <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1">{label}</label>
      {multiline ? (
        <textarea className={cls} rows={rows || 3} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} />
      ) : (
        <input className={cls} type="text" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} />
      )}
    </div>
  );
}
