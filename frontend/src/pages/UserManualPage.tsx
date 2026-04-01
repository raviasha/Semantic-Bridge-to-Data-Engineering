import { useState } from 'react';
import type { ReactNode } from 'react';
import {
  BookOpen, Database, Sparkles, History, Search,
  ChevronDown, ChevronRight, ArrowRight, Layers, Pencil,
  AlertTriangle
} from 'lucide-react';

type Section = {
  id: string;
  title: string;
  icon: any;
  content: ReactNode;
};

export function UserManualPage() {
  const [expandedSection, setExpandedSection] = useState<string | null>('overview');

  const toggle = (id: string) =>
    setExpandedSection((prev) => (prev === id ? null : id));

  const sections: Section[] = [
    {
      id: 'overview',
      title: 'Overview',
      icon: BookOpen,
      content: (
        <div className="space-y-3">
          <p>
            <strong>Semantic Bridge</strong> is a prototype tool designed to eliminate the translation lag
            between <em>domain experts</em> (HR, Benefits, Finance teams) and <em>data engineers</em>.
          </p>
          <p>
            It provides a centralized, AI-powered interface for browsing, understanding, and managing
            the metadata of an HCM (Human Capital Management) Benefits data schema — covering
            <strong> 6 applications</strong>, <strong>12 tables</strong>, and <strong>93 columns</strong>.
          </p>
          <div className="bg-[var(--color-bg-tertiary)] rounded-lg p-4 mt-4">
            <h4 className="text-sm font-semibold text-[var(--color-primary-light)] mb-2">Key Capabilities</h4>
            <ul className="space-y-1.5 text-sm">
              <li className="flex items-start gap-2"><ArrowRight className="w-4 h-4 mt-0.5 text-[var(--color-primary-light)] shrink-0" /> Application-first schema browsing with rich column metadata</li>
              <li className="flex items-start gap-2"><ArrowRight className="w-4 h-4 mt-0.5 text-[var(--color-primary-light)] shrink-0" /> Natural language updates powered by GPT-4o</li>
              <li className="flex items-start gap-2"><ArrowRight className="w-4 h-4 mt-0.5 text-[var(--color-primary-light)] shrink-0" /> Cross-application impact analysis with AI risk assessment</li>
              <li className="flex items-start gap-2"><ArrowRight className="w-4 h-4 mt-0.5 text-[var(--color-primary-light)] shrink-0" /> Version-tracked change history with undo support</li>
              <li className="flex items-start gap-2"><ArrowRight className="w-4 h-4 mt-0.5 text-[var(--color-primary-light)] shrink-0" /> Preview-before-confirm workflow for all AI-driven changes</li>
            </ul>
          </div>
        </div>
      ),
    },
    {
      id: 'navigation',
      title: 'Navigating Applications & Tables',
      icon: Database,
      content: (
        <div className="space-y-4">
          <div>
            <h4 className="text-sm font-semibold text-[var(--color-text)] mb-2">Step 1 — Select an Application</h4>
            <p className="text-sm">
              The home screen shows <strong>6 application cards</strong> (e.g., Benefits Administration,
              Enrollment Portal, HR Analytics Hub). Click any card to enter that application's scope.
            </p>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-[var(--color-text)] mb-2">Step 2 — Browse Tables</h4>
            <p className="text-sm">
              Inside an application, you'll see the relevant tables listed. Click a table name to
              expand it and reveal its columns. A badge shows the column count.
            </p>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-[var(--color-text)] mb-2">Step 3 — Select a Column</h4>
            <p className="text-sm">
              Click any column to open its <strong>detail panel</strong> on the right side. This
              shows all metadata fields: description, business rules, formula, data sensitivity,
              domain expert, usage in metrics, and more.
            </p>
          </div>
          <div className="bg-[var(--color-bg-tertiary)] rounded-lg p-4">
            <h4 className="text-sm font-semibold text-[var(--color-warning)] mb-2">💡 Tip</h4>
            <p className="text-sm">
              Use the <strong>← Back</strong> button at the top of the left panel to go back to
              the application list at any time.
            </p>
          </div>
        </div>
      ),
    },
    {
      id: 'metadata',
      title: 'Viewing & Editing Metadata',
      icon: Pencil,
      content: (
        <div className="space-y-4">
          <div>
            <h4 className="text-sm font-semibold text-[var(--color-text)] mb-2">Column Detail Panel</h4>
            <p className="text-sm">
              When a column is selected, the right panel shows its complete metadata:
            </p>
            <ul className="mt-2 space-y-1 text-sm ml-4">
              <li>• <strong>Description</strong> — What the column represents</li>
              <li>• <strong>Business Rules</strong> — Rules governing the column's data</li>
              <li>• <strong>Formula / Derivation</strong> — How the value is calculated</li>
              <li>• <strong>Used in Metrics</strong> — Which metrics reference this column</li>
              <li>• <strong>Data Sensitivity</strong> — PII, PHI, Financial, or Public</li>
              <li>• <strong>Data Type & Domain Expert</strong></li>
              <li>• <strong>Source System & Validated Date</strong></li>
            </ul>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-[var(--color-text)] mb-2">Inline Editing</h4>
            <p className="text-sm">
              Click the <strong>✏️ Edit</strong> button in the detail panel header to enter edit mode.
              All fields become editable text inputs. When done:
            </p>
            <ul className="mt-2 space-y-1 text-sm ml-4">
              <li>• Click <strong>💾 Save</strong> to persist your changes</li>
              <li>• Click <strong>✕ Cancel</strong> to discard edits</li>
            </ul>
          </div>
          <div className="bg-[var(--color-bg-tertiary)] rounded-lg p-4">
            <h4 className="text-sm font-semibold text-[var(--color-warning)] mb-2">⚠️ Impact Analysis</h4>
            <p className="text-sm">
              If the column you're editing is <strong>shared across multiple applications</strong>,
              saving will trigger an <strong>AI-powered impact analysis</strong>. A panel shows
              which other applications would be affected and the risk level (Low / Medium / High / Critical).
              You can then <strong>Confirm</strong> or <strong>Cancel</strong> the save.
            </p>
          </div>
        </div>
      ),
    },
    {
      id: 'nl-commands',
      title: 'Natural Language Commands',
      icon: Sparkles,
      content: (
        <div className="space-y-4">
          <p className="text-sm">
            The <strong>AI Command Bar</strong> appears at the bottom of the right panel when a
            column is selected. It lets you modify column metadata using plain English.
          </p>
          <div>
            <h4 className="text-sm font-semibold text-[var(--color-text)] mb-2">How It Works</h4>
            <ol className="space-y-2 text-sm ml-4">
              <li><strong>1.</strong> Type an instruction like <em>"Add a business rule that values must be non-negative"</em></li>
              <li><strong>2.</strong> Press Enter or click Send</li>
              <li><strong>3.</strong> The AI generates a <strong>preview</strong> showing proposed changes as side-by-side diffs</li>
              <li><strong>4.</strong> If the column is shared across apps, you'll see an <strong>impact analysis</strong> with risk levels</li>
              <li><strong>5.</strong> Click <strong>✅ Confirm & Apply</strong> to save, or <strong>✕ Discard</strong> to reject</li>
            </ol>
          </div>
          <div className="bg-[var(--color-bg-tertiary)] rounded-lg p-4">
            <h4 className="text-sm font-semibold text-[var(--color-primary-light)] mb-2">Example Commands</h4>
            <div className="space-y-2 text-sm">
              <div className="bg-[var(--color-bg-secondary)] rounded px-3 py-2 font-mono text-xs">
                "Update the formula to include a 10% employer surcharge"
              </div>
              <div className="bg-[var(--color-bg-secondary)] rounded px-3 py-2 font-mono text-xs">
                "Add a rule: enrollment_date must be within open enrollment window"
              </div>
              <div className="bg-[var(--color-bg-secondary)] rounded px-3 py-2 font-mono text-xs">
                "Change data sensitivity to PHI and update the description to mention HIPAA"
              </div>
              <div className="bg-[var(--color-bg-secondary)] rounded px-3 py-2 font-mono text-xs">
                "Remove the third business rule about deductible caps"
              </div>
            </div>
          </div>
          <div className="bg-[var(--color-bg-tertiary)] rounded-lg p-4">
            <h4 className="text-sm font-semibold text-[var(--color-warning)] mb-2">💡 Tips</h4>
            <ul className="space-y-1 text-sm">
              <li>• The AI updates <strong>all logically affected fields</strong> — not just the one you mention</li>
              <li>• List fields (rules, metrics) are <strong>replaced entirely</strong>, not appended</li>
              <li>• Every NL change creates a <strong>versioned history entry</strong> you can undo later</li>
            </ul>
          </div>
        </div>
      ),
    },
    {
      id: 'impact',
      title: 'Cross-Application Impact Analysis',
      icon: AlertTriangle,
      content: (
        <div className="space-y-4">
          <p className="text-sm">
            Many columns are shared across multiple applications (e.g., <em>employee_id</em> appears
            in Benefits Admin, Enrollment Portal, and HR Analytics). Changing these columns can
            have downstream effects.
          </p>
          <div>
            <h4 className="text-sm font-semibold text-[var(--color-text)] mb-2">When Does It Trigger?</h4>
            <ul className="text-sm space-y-1 ml-4">
              <li>• When you <strong>save inline edits</strong> on a shared column</li>
              <li>• When you <strong>confirm an NL command</strong> that modifies a shared column</li>
            </ul>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-[var(--color-text)] mb-2">What It Shows</h4>
            <ul className="text-sm space-y-1 ml-4">
              <li>• <strong>Affected applications</strong> — which other apps use this column</li>
              <li>• <strong>Risk level</strong> — Low (green), Medium (yellow), High (orange), Critical (red)</li>
              <li>• <strong>AI explanation</strong> — why the change is risky and what might break</li>
            </ul>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-[var(--color-text)] mb-2">Usage Badge</h4>
            <p className="text-sm">
              In the column detail panel header, you'll see a badge like
              <span className="inline-flex items-center gap-1 mx-1 px-2 py-0.5 rounded bg-[var(--color-bg-tertiary)] text-xs font-medium">
                <Layers className="w-3 h-3" /> Used in 4 apps
              </span>
              showing how many applications reference the column.
            </p>
          </div>
        </div>
      ),
    },
    {
      id: 'history',
      title: 'Version History & Undo',
      icon: History,
      content: (
        <div className="space-y-4">
          <p className="text-sm">
            Every metadata change is tracked with full version history. Changes from the same
            operation are grouped into <strong>version numbers</strong>.
          </p>
          <div>
            <h4 className="text-sm font-semibold text-[var(--color-text)] mb-2">Viewing History</h4>
            <p className="text-sm">
              Click the <strong>🕐 History</strong> button in the column detail panel to open the
              version history. Each version group shows:
            </p>
            <ul className="mt-2 text-sm space-y-1 ml-4">
              <li>• <strong>Version number</strong> and timestamp</li>
              <li>• <strong>Source badge</strong> — "manual" (inline edit) or "nl-command" (AI-driven)</li>
              <li>• <strong>Field-level diffs</strong> — old value → new value for each changed field</li>
            </ul>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-[var(--color-text)] mb-2">Undoing Changes</h4>
            <ul className="text-sm space-y-1 ml-4">
              <li>• Click the <strong>↩️ Undo</strong> button on a version to revert that specific field change</li>
              <li>• Undo operations are <strong>silent</strong> — they restore the old value without creating a new version entry</li>
              <li>• A confirmation toast will appear: <em>"Change undone"</em></li>
            </ul>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-[var(--color-text)] mb-2">Deleting History</h4>
            <p className="text-sm">
              Click the <strong>🗑 Delete</strong> button on a version group to permanently remove
              those history entries. This does <em>not</em> revert the changes — it only removes the
              audit trail.
            </p>
          </div>
          <div className="bg-[var(--color-bg-tertiary)] rounded-lg p-4">
            <h4 className="text-sm font-semibold text-[var(--color-primary-light)] mb-2">Navigation</h4>
            <p className="text-sm">
              Use the <strong>← Back to Metadata</strong> button at the top of the history panel
              to return to the column's metadata view.
            </p>
          </div>
        </div>
      ),
    },
    {
      id: 'applications',
      title: 'Applications Reference',
      icon: Layers,
      content: (
        <div className="space-y-4">
          <p className="text-sm">The system includes 6 HCM Benefits applications:</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {[
              { name: 'Benefits Administration', desc: 'Core plan management, eligibility rules, and enrollment processing' },
              { name: 'Enrollment Portal', desc: 'Employee-facing enrollment interface with plan selection and life events' },
              { name: 'HR Analytics Hub', desc: 'Workforce analytics, cost analysis, and benefits utilization reporting' },
              { name: 'Compliance Engine', desc: 'ACA compliance, COBRA administration, and regulatory reporting' },
              { name: 'Payroll Integration', desc: 'Benefits deductions, employer contributions, and payroll sync' },
              { name: 'Employee Self-Service', desc: 'Benefits dashboard, claims status, and dependent management' },
            ].map((app) => (
              <div key={app.name} className="bg-[var(--color-bg-tertiary)] rounded-lg p-3">
                <h4 className="text-sm font-semibold text-[var(--color-text)]">{app.name}</h4>
                <p className="text-xs text-[var(--color-text-muted)] mt-1">{app.desc}</p>
              </div>
            ))}
          </div>
          <div>
            <h4 className="text-sm font-semibold text-[var(--color-text)] mb-2 mt-4">Schema Tables</h4>
            <p className="text-sm">The schema spans 12 tables:</p>
            <div className="mt-2 grid grid-cols-2 md:grid-cols-3 gap-2 text-xs font-mono">
              {[
                'employees', 'benefit_plans', 'benefit_plan_options', 'employee_enrollments',
                'enrollment_elections', 'dependents', 'dependent_coverage', 'life_events',
                'benefit_costs', 'eligibility_rules', 'carrier_feeds', 'audit_log',
              ].map((t) => (
                <div key={t} className="bg-[var(--color-bg-secondary)] rounded px-2 py-1.5 text-[var(--color-primary-light)]">{t}</div>
              ))}
            </div>
          </div>
        </div>
      ),
    },
    {
      id: 'glossary',
      title: 'Glossary',
      icon: Search,
      content: (
        <div className="space-y-2">
          <div className="grid gap-3">
            {[
              { term: 'Metadata', def: 'Descriptive information about a column — its meaning, rules, formula, sensitivity level, and ownership.' },
              { term: 'Business Rules', def: 'Constraints or logic governing how a column\'s data should behave (e.g., "Must be ≥ 0", "Required for active employees").' },
              { term: 'Formula / Derivation', def: 'How a column\'s value is calculated from other columns (e.g., "Total premium − employee contribution").' },
              { term: 'Data Sensitivity', def: 'Classification of data protection level: PII (personally identifiable), PHI (health info), Financial, or Public.' },
              { term: 'Impact Analysis', def: 'AI-driven risk assessment that evaluates how changing a shared column affects other applications.' },
              { term: 'NL Command', def: 'A natural language instruction to the AI to modify column metadata (e.g., "Add a rule that enrollment must be within 30 days").' },
              { term: 'Version', def: 'A numbered snapshot of metadata changes. All fields changed in a single operation share one version number.' },
              { term: 'Domain Expert', def: 'The person responsible for defining and validating the business meaning of a column.' },
              { term: 'Source System', def: 'The upstream system where the column\'s data originates (e.g., Workday, PeopleSoft).' },
            ].map((item) => (
              <div key={item.term} className="bg-[var(--color-bg-tertiary)] rounded-lg p-3">
                <h4 className="text-sm font-semibold text-[var(--color-primary-light)]">{item.term}</h4>
                <p className="text-xs text-[var(--color-text-muted)] mt-1">{item.def}</p>
              </div>
            ))}
          </div>
        </div>
      ),
    },
  ];

  return (
    <div className="flex flex-col h-screen">
      <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto w-full">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-[var(--color-primary)] flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-[var(--color-text)]">User Manual</h1>
              <p className="text-sm text-[var(--color-text-muted)]">Semantic Bridge — Prototype v0.1</p>
            </div>
          </div>
          <p className="text-sm text-[var(--color-text-muted)] mt-3 leading-relaxed">
            This guide covers everything you need to know to browse schemas, edit metadata,
            use AI-powered natural language commands, and manage version history.
          </p>
        </div>

        {/* Accordion Sections */}
        <div className="space-y-2">
          {sections.map((section) => {
            const Icon = section.icon;
            const isOpen = expandedSection === section.id;
            return (
              <div key={section.id} className="bg-[var(--color-bg-secondary)] rounded-xl border border-[var(--color-border)] overflow-hidden">
                <button
                  onClick={() => toggle(section.id)}
                  className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-[var(--color-bg-tertiary)] transition-colors"
                >
                  {isOpen ? (
                    <ChevronDown className="w-4 h-4 text-[var(--color-primary-light)]" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-[var(--color-text-muted)]" />
                  )}
                  <Icon className={`w-5 h-5 ${isOpen ? 'text-[var(--color-primary-light)]' : 'text-[var(--color-text-muted)]'}`} />
                  <span className={`text-sm font-semibold ${isOpen ? 'text-[var(--color-text)]' : 'text-[var(--color-text-muted)]'}`}>
                    {section.title}
                  </span>
                </button>
                {isOpen && (
                  <div className="px-5 pb-5 pt-1 text-[var(--color-text-muted)] text-sm leading-relaxed border-t border-[var(--color-border)]">
                    {section.content}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-xs text-[var(--color-text-muted)] pb-6">
          Semantic Bridge Prototype v0.1 • Built with React, FastAPI & GPT-4o
        </div>
      </div>
    </div>
  );
}
