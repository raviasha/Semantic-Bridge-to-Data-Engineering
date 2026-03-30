import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { ArrowLeft, Copy, Check, Download, FileText, Table, Filter } from 'lucide-react';
import { api } from '../api';

export function ReviewPage() {
  const { interviewId } = useParams<{ interviewId: string }>();
  const navigate = useNavigate();
  const [result, setResult] = useState<any>(null);
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (interviewId) {
      api.generateSQL(interviewId)
        .then(setResult)
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [interviewId]);

  const handleCopy = () => {
    if (result?.sql) {
      navigator.clipboard.writeText(result.sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownload = () => {
    if (result?.sql) {
      const blob = new Blob([result.sql], { type: 'text/sql' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${result.documentation?.model_name || 'query'}.sql`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-[var(--color-text-muted)]">
        Generating SQL...
      </div>
    );
  }

  const doc = result?.documentation;

  return (
    <div className="flex h-full">
      {/* Left pane — Documentation */}
      <div className="w-[400px] border-r border-[var(--color-border)] overflow-y-auto bg-[var(--color-bg-secondary)]">
        <div className="p-4 border-b border-[var(--color-border)] flex items-center gap-3">
          <button
            onClick={() => navigate(`/interview/${interviewId}/flow`)}
            className="p-1.5 rounded-lg hover:bg-[var(--color-bg-tertiary)] text-[var(--color-text-muted)]"
          >
            <ArrowLeft size={18} />
          </button>
          <h2 className="font-semibold">Review & Approve</h2>
        </div>

        {doc && (
          <div className="p-4 space-y-6">
            {/* Model Info */}
            <div>
              <h3 className="text-sm font-semibold text-[var(--color-text-muted)] uppercase tracking-wide mb-2 flex items-center gap-2">
                <FileText size={14} />
                Model
              </h3>
              <p className="font-mono text-sm text-[var(--color-primary-light)]">{doc.model_name}</p>
              <p className="text-sm text-[var(--color-text-muted)] mt-2">{doc.description}</p>
              <div className="mt-3 flex items-center gap-3 text-xs">
                <span className="px-2 py-0.5 bg-[var(--color-bg-tertiary)] rounded">
                  Grain: {doc.grain}
                </span>
                <span className="px-2 py-0.5 bg-green-900/50 text-green-300 rounded">
                  Score: {doc.confidence_score}
                </span>
              </div>
            </div>

            {/* Source Tables */}
            <div>
              <h3 className="text-sm font-semibold text-[var(--color-text-muted)] uppercase tracking-wide mb-2 flex items-center gap-2">
                <Table size={14} />
                Source Tables
              </h3>
              <div className="space-y-1">
                {doc.source_tables?.map((t: string) => (
                  <div key={t} className="text-xs font-mono text-[var(--color-text)] px-2 py-1 bg-[var(--color-bg-tertiary)] rounded">
                    {t}
                  </div>
                ))}
              </div>
            </div>

            {/* Output Columns */}
            <div>
              <h3 className="text-sm font-semibold text-[var(--color-text-muted)] uppercase tracking-wide mb-2">
                Output Columns
              </h3>
              <div className="space-y-2">
                {doc.columns?.map((col: any) => (
                  <div key={col.name} className="text-xs">
                    <span className="font-mono text-[var(--color-primary-light)]">{col.name}</span>
                    <p className="text-[var(--color-text-muted)] mt-0.5">{col.description}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Filters */}
            <div>
              <h3 className="text-sm font-semibold text-[var(--color-text-muted)] uppercase tracking-wide mb-2 flex items-center gap-2">
                <Filter size={14} />
                Filters Applied
              </h3>
              <div className="space-y-1">
                {doc.filters_applied?.map((f: string, i: number) => (
                  <div key={i} className="text-xs font-mono text-[var(--color-text-muted)] px-2 py-1 bg-[var(--color-bg-tertiary)] rounded">
                    {f}
                  </div>
                ))}
              </div>
            </div>

            {/* Lint Status */}
            <div className="flex items-center gap-2 p-3 rounded-lg bg-green-900/20 border border-green-800">
              <Check size={14} className="text-green-400" />
              <span className="text-sm text-green-300">sqlfluff lint: {result?.lint_status}</span>
            </div>
          </div>
        )}
      </div>

      {/* Right pane — SQL */}
      <div className="flex-1 flex flex-col">
        <div className="px-4 py-3 border-b border-[var(--color-border)] flex items-center justify-between bg-[var(--color-bg)]">
          <div className="flex items-center gap-2 text-sm">
            <span className="font-mono text-[var(--color-text-muted)]">{doc?.model_name}.sql</span>
            <span className="text-xs px-2 py-0.5 bg-blue-900/50 text-blue-300 rounded border border-blue-800">
              {result?.dialect}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text)] border border-[var(--color-border)] rounded-lg hover:bg-[var(--color-bg-secondary)] transition-colors"
            >
              {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
              {copied ? 'Copied!' : 'Copy'}
            </button>
            <button
              onClick={handleDownload}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text)] border border-[var(--color-border)] rounded-lg hover:bg-[var(--color-bg-secondary)] transition-colors"
            >
              <Download size={14} />
              Download
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-auto">
          {result?.sql ? (
            <SyntaxHighlighter
              language="sql"
              style={oneDark}
              customStyle={{
                margin: 0,
                padding: '1.5rem',
                background: '#0f172a',
                fontSize: '13px',
                lineHeight: '1.6',
                height: '100%',
              }}
              showLineNumbers
            >
              {result.sql}
            </SyntaxHighlighter>
          ) : (
            <div className="flex items-center justify-center h-full text-[var(--color-text-muted)]">
              No SQL generated yet
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
