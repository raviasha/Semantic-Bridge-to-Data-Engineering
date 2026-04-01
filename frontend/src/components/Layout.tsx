import { useState } from 'react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Database, MessageSquare, Plus, ArrowRight, BookOpen } from 'lucide-react';
import { api } from '../api';

const navItems = [
  { path: '/', label: 'Schema Browser', icon: Database },
  { path: '/manual', label: 'User Manual', icon: BookOpen },
];

export function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [showNewInterview, setShowNewInterview] = useState(false);
  const [ivTitle, setIvTitle] = useState('');
  const [ivLoading, setIvLoading] = useState(false);

  const handleStartInterview = async () => {
    if (!ivTitle.trim()) return;
    setIvLoading(true);
    try {
      const interview: any = await api.startInterview(ivTitle);
      navigate(`/interview/${interview.interview_id}`);
      setIvTitle('');
      setShowNewInterview(false);
    } catch {
      // ignore
    } finally {
      setIvLoading(false);
    }
  };

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <aside className="w-64 bg-[var(--color-bg-secondary)] border-r border-[var(--color-border)] flex flex-col">
        <div className="p-4 border-b border-[var(--color-border)]">
          <Link to="/" className="flex items-center gap-2 no-underline">
            <div className="w-8 h-8 rounded-lg bg-[var(--color-primary)] flex items-center justify-center">
              <MessageSquare size={18} className="text-white" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-[var(--color-text)]">Semantic Bridge</h1>
              <p className="text-xs text-[var(--color-text-muted)]">Prototype v0.1</p>
            </div>
          </Link>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm no-underline transition-colors ${
                  isActive
                    ? 'bg-[var(--color-primary)] text-white'
                    : 'text-[var(--color-text-muted)] hover:bg-[var(--color-bg-tertiary)] hover:text-[var(--color-text)]'
                }`}
              >
                <item.icon size={18} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* New Interview quick-launch */}
        <div className="p-3 border-t border-[var(--color-border)]">
          {!showNewInterview ? (
            <button
              onClick={() => setShowNewInterview(true)}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg bg-[var(--color-primary)]/20 text-[var(--color-primary-light)] hover:bg-[var(--color-primary)]/30 transition-colors"
            >
              <Plus size={16} /> New Interview
            </button>
          ) : (
            <div className="space-y-2">
              <input
                type="text"
                placeholder="Metric name…"
                value={ivTitle}
                onChange={(e) => setIvTitle(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleStartInterview()}
                autoFocus
                className="w-full px-3 py-2 text-sm bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)]"
              />
              <div className="flex gap-2">
                <button
                  onClick={handleStartInterview}
                  disabled={!ivTitle.trim() || ivLoading}
                  className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 text-xs bg-[var(--color-primary)] text-white rounded-lg disabled:opacity-50"
                >
                  {ivLoading ? '…' : 'Start'} <ArrowRight size={12} />
                </button>
                <button
                  onClick={() => { setShowNewInterview(false); setIvTitle(''); }}
                  className="px-2 py-1.5 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="p-4 border-t border-[var(--color-border)]">
          <div className="text-xs text-[var(--color-text-muted)]">
            <p>HCM Analytics Schema</p>
            <p className="mt-1">12 tables • Metadata only</p>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
