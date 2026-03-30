import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, MessageSquare, ArrowRight, Clock } from 'lucide-react';
import { api } from '../api';

export function DashboardPage() {
  const navigate = useNavigate();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [interviews, setInterviews] = useState<any[]>([]);
  const [showNew, setShowNew] = useState(false);
  const [loading, setLoading] = useState(false);

  const loadInterviews = async () => {
    try {
      const data = await api.listInterviews();
      setInterviews(data);
    } catch {
      // Backend may not be up yet — that's fine for UI preview
    }
  };

  useState(() => {
    loadInterviews();
  });

  const handleStart = async () => {
    if (!title.trim()) return;
    setLoading(true);
    try {
      const interview: any = await api.startInterview(title, description);
      navigate(`/interview/${interview.interview_id}`);
    } catch {
      alert('Backend not running — start Docker Compose first');
    } finally {
      setLoading(false);
    }
  };

  const statusBadge = (status: string) => {
    const colors: Record<string, string> = {
      in_progress: 'bg-blue-900/50 text-blue-300 border-blue-700',
      needs_review: 'bg-yellow-900/50 text-yellow-300 border-yellow-700',
      ready: 'bg-green-900/50 text-green-300 border-green-700',
    };
    return (
      <span className={`text-xs px-2 py-0.5 rounded-full border ${colors[status] || colors.in_progress}`}>
        {status.replace('_', ' ')}
      </span>
    );
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text)]">Semantic Bridge</h1>
          <p className="text-[var(--color-text-muted)] mt-1">
            Translate business metrics into validated data transformations
          </p>
        </div>
        <button
          onClick={() => setShowNew(!showNew)}
          className="flex items-center gap-2 px-4 py-2 bg-[var(--color-primary)] text-white rounded-lg hover:bg-[var(--color-primary-dark)] transition-colors"
        >
          <Plus size={18} />
          New Interview
        </button>
      </div>

      {/* New Interview Form */}
      {showNew && (
        <div className="mb-8 p-6 bg-[var(--color-bg-secondary)] rounded-xl border border-[var(--color-border)]">
          <h2 className="text-lg font-semibold mb-4">Start a New Interview</h2>
          <p className="text-sm text-[var(--color-text-muted)] mb-4">
            Describe the metric or report you need. The AI will interview you to capture precise requirements,
            then generate validated SQL grounded against your warehouse schema.
          </p>
          <div className="space-y-3">
            <input
              type="text"
              placeholder="Metric name (e.g., 'Medical Enrollment Rate by Department')"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)]"
            />
            <textarea
              placeholder="Brief description (optional) — e.g., 'Need to track how many eligible employees are enrolled in medical plans, broken down by department'"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)] resize-none"
            />
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowNew(false)}
                className="px-4 py-2 text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleStart}
                disabled={!title.trim() || loading}
                className="flex items-center gap-2 px-4 py-2 bg-[var(--color-primary)] text-white rounded-lg hover:bg-[var(--color-primary-dark)] disabled:opacity-50 transition-colors"
              >
                {loading ? 'Starting...' : 'Start Interview'}
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Interview List */}
      <div>
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Clock size={18} className="text-[var(--color-text-muted)]" />
          Recent Interviews
        </h2>
        {interviews.length === 0 ? (
          <div className="text-center py-16 bg-[var(--color-bg-secondary)] rounded-xl border border-[var(--color-border)]">
            <MessageSquare size={48} className="mx-auto text-[var(--color-text-muted)] mb-4" />
            <p className="text-[var(--color-text-muted)]">No interviews yet</p>
            <p className="text-sm text-[var(--color-text-muted)] mt-1">
              Click "New Interview" to get started
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {interviews.map((iv: any) => (
              <button
                key={iv.interview_id}
                onClick={() => navigate(`/interview/${iv.interview_id}`)}
                className="w-full text-left p-4 bg-[var(--color-bg-secondary)] rounded-xl border border-[var(--color-border)] hover:border-[var(--color-primary)] transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium">{iv.title}</h3>
                    <p className="text-sm text-[var(--color-text-muted)] mt-1">
                      {iv.turn_count} turns • Score: {iv.confidence_score}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    {statusBadge(iv.status)}
                    <ArrowRight size={16} className="text-[var(--color-text-muted)]" />
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
