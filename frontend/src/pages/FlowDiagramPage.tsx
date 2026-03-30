import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ReactFlow,
  Background,
  Controls,
  type Node,
  type Edge,
  Position,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { ArrowLeft, ArrowRight, Check, X } from 'lucide-react';
import { api } from '../api';

const nodeColors: Record<string, { bg: string; border: string; text: string }> = {
  source: { bg: '#1e3a5f', border: '#3b82f6', text: '#93c5fd' },
  filter: { bg: '#3b1f1f', border: '#ef4444', text: '#fca5a5' },
  join: { bg: '#1f3b2f', border: '#10b981', text: '#6ee7b7' },
  aggregation: { bg: '#3b2f1f', border: '#f59e0b', text: '#fcd34d' },
  output: { bg: '#2e1f5e', border: '#8b5cf6', text: '#c4b5fd' },
};

function CustomNode({ data }: { data: { label: string; nodeType: string } }) {
  const colors = nodeColors[data.nodeType] || nodeColors.source;
  return (
    <div
      className="px-4 py-3 rounded-lg border-2 min-w-[180px] text-center"
      style={{
        background: colors.bg,
        borderColor: colors.border,
        color: colors.text,
      }}
    >
      <div className="text-[10px] uppercase tracking-wide opacity-60 mb-1">
        {data.nodeType}
      </div>
      <div className="text-xs font-mono whitespace-pre-line">{data.label}</div>
    </div>
  );
}

const nodeTypes = { custom: CustomNode };

export function FlowDiagramPage() {
  const { interviewId } = useParams<{ interviewId: string }>();
  const navigate = useNavigate();
  const [flowData, setFlowData] = useState<any>(null);

  useEffect(() => {
    if (interviewId) {
      api.getFlowDiagram(interviewId).then(setFlowData).catch(() => {});
    }
  }, [interviewId]);

  const { nodes, edges } = useMemo(() => {
    if (!flowData) return { nodes: [] as Node[], edges: [] as Edge[] };

    const nodeList: Node[] = flowData.nodes.map((n: any, i: number) => ({
      id: n.id,
      type: 'custom',
      position: { x: 200 * (i % 4), y: Math.floor(i / 4) * 140 + 50 },
      data: { label: n.label, nodeType: n.type },
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
    }));

    // Auto-layout: arrange by type layers
    const layers: Record<string, number> = { source: 0, filter: 1, join: 2, aggregation: 3, output: 4 };
    const layerCounts: Record<number, number> = {};
    nodeList.forEach((n) => {
      const layer = layers[(n.data as any).nodeType] ?? 2;
      const count = layerCounts[layer] || 0;
      n.position = { x: count * 280 + 50, y: layer * 160 + 40 };
      layerCounts[layer] = count + 1;
    });

    const edgeList: Edge[] = flowData.edges.map((e: any, i: number) => ({
      id: `e${i}`,
      source: e.source,
      target: e.target,
      animated: true,
      style: { stroke: '#64748b', strokeWidth: 2 },
    }));

    return { nodes: nodeList, edges: edgeList };
  }, [flowData]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-6 py-3 border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(`/interview/${interviewId}`)}
            className="p-1.5 rounded-lg hover:bg-[var(--color-bg-tertiary)] text-[var(--color-text-muted)]"
          >
            <ArrowLeft size={18} />
          </button>
          <h2 className="font-semibold">Logic Flow Diagram</h2>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate(`/interview/${interviewId}`)}
            className="flex items-center gap-2 px-3 py-1.5 border border-red-700 text-red-400 rounded-lg text-sm hover:bg-red-900/30 transition-colors"
          >
            <X size={14} />
            Reject & Revise
          </button>
          <button
            onClick={() => navigate(`/interview/${interviewId}/review`)}
            className="flex items-center gap-2 px-3 py-1.5 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 transition-colors"
          >
            <Check size={14} />
            Confirm & Generate SQL
            <ArrowRight size={14} />
          </button>
        </div>
      </div>

      {/* Legend */}
      <div className="px-6 py-2 border-b border-[var(--color-border)] flex items-center gap-4 text-xs text-[var(--color-text-muted)]">
        {Object.entries(nodeColors).map(([type, colors]) => (
          <div key={type} className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded" style={{ background: colors.border }} />
            <span className="capitalize">{type}</span>
          </div>
        ))}
      </div>

      {/* Flow diagram */}
      <div className="flex-1">
        {nodes.length > 0 ? (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.3 }}
            proOptions={{ hideAttribution: true }}
          >
            <Background color="#334155" gap={20} />
            <Controls />
          </ReactFlow>
        ) : (
          <div className="flex items-center justify-center h-full text-[var(--color-text-muted)]">
            Loading flow diagram...
          </div>
        )}
      </div>
    </div>
  );
}
