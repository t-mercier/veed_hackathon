/**
 * Custom React Flow node for explanation parts (blocks, phases, concepts).
 */
import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";

const KIND_STYLES: Record<string, { bg: string; border: string; icon: string }> = {
  phase:    { bg: "#1e3a5f", border: "#60a5fa", icon: "🔷" },
  concept:  { bg: "#4c1d95", border: "#a78bfa", icon: "💡" },
  function: { bg: "#064e3b", border: "#34d399", icon: "⚡" },
  variable: { bg: "#78350f", border: "#fbbf24", icon: "📌" },
  step:     { bg: "#7c2d12", border: "#fb923c", icon: "➡️" },
  block:    { bg: "#312e81", border: "#818cf8", icon: "📦" },
};

const DEFAULT_STYLE = KIND_STYLES.phase;

export interface PartNodeData {
  label: string;
  kind: string;
  description: string;
  highlighted: boolean;
  dimmed: boolean;
}

function PartNode({ data }: NodeProps<PartNodeData>) {
  const style = KIND_STYLES[data.kind] || DEFAULT_STYLE;

  return (
    <div
      style={{
        background: style.bg,
        borderColor: style.border,
        borderWidth: 2,
        borderStyle: "solid",
        borderRadius: 12,
        padding: "10px 16px",
        minWidth: 140,
        maxWidth: 220,
        opacity: data.dimmed ? 0.3 : 1,
        transform: data.highlighted ? "scale(1.05)" : data.dimmed ? "scale(0.95)" : "scale(1)",
        boxShadow: data.highlighted ? `0 0 16px ${style.border}60` : "0 4px 12px rgba(0,0,0,0.3)",
        transition: "all 0.5s ease",
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: "#ffffff66", width: 8, height: 8 }} />
      <Handle type="source" position={Position.Bottom} style={{ background: "#ffffff66", width: 8, height: 8 }} />
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
        <span style={{ fontSize: 14 }}>{style.icon}</span>
        <span style={{ fontSize: 13, fontWeight: 600, color: "#fff" }}>
          {data.label}
        </span>
      </div>
      {data.description && !data.dimmed && (
        <p style={{ fontSize: 10, lineHeight: 1.3, color: "#ffffff99", margin: 0 }}>
          {data.description}
        </p>
      )}
    </div>
  );
}

export default memo(PartNode);
