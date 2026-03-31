/**
 * React Flow renderer for prompt/concept explanation.
 *
 * Takes an explanation (parts + relationships) and storyboard (scenes) and renders
 * a scene-driven visual walkthrough. Closely mirrors RepoExplainerFlow but adapted
 * for the prompt explanation data shapes.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactFlow, {
  Background,
  type Edge,
  type Node,
  useNodesState,
  useEdgesState,
  useReactFlow,
  ReactFlowProvider,
  MarkerType,
} from "reactflow";
import dagre from "@dagrejs/dagre";
import "reactflow/dist/style.css";

import PartNode from "./PartNode";

// ── Types matching backend prompt_models ────────────────────────────────────

interface Part {
  id: string;
  label: string;
  kind: string;
  description: string;
}

interface Relationship {
  id: string;
  from: string;
  to: string;
  label: string;
}

interface Explanation {
  title: string;
  summary: string;
  explanation_type: string;
  parts: Part[];
  relationships: Relationship[];
}

interface ScenePanel {
  title: string;
  bullets: string[];
}

interface PromptScene {
  id: string;
  title: string;
  goal: string;
  visible_parts: string[];
  highlighted_parts: string[];
  highlighted_relationships: string[];
  camera_mode: string;
  focus_part: string | null;
  narration: string;
  panel: ScenePanel | null;
}

interface Storyboard {
  scenes: PromptScene[];
}

interface PromptExplainerFlowProps {
  explanation: Explanation;
  storyboard: Storyboard;
  /** When provided, scene is controlled externally (by PromptPlayer). */
  activeSceneIndex?: number;
}

// ── Dagre layout ────────────────────────────────────────────────────────────

const NODE_WIDTH = 200;
const NODE_HEIGHT = 90;

function layoutParts(
  parts: Part[],
  relationships: Relationship[],
): Map<string, { x: number; y: number }> {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", ranksep: 120, nodesep: 70 });

  parts.forEach((p) => {
    g.setNode(p.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });
  relationships.forEach((r) => {
    if (g.hasNode(r.from) && g.hasNode(r.to)) {
      g.setEdge(r.from, r.to);
    }
  });

  dagre.layout(g);

  const positions = new Map<string, { x: number; y: number }>();
  parts.forEach((p) => {
    const node = g.node(p.id);
    if (node) {
      positions.set(p.id, { x: node.x - NODE_WIDTH / 2, y: node.y - NODE_HEIGHT / 2 });
    }
  });
  return positions;
}

// ── Edge colors ─────────────────────────────────────────────────────────────

const EDGE_COLOR_ACTIVE = "#60a5fa";
const EDGE_COLOR_DIM = "#60a5fa40";

// ── Node types ──────────────────────────────────────────────────────────────

const nodeTypes = { part: PartNode };

// ── Auto-play interval ──────────────────────────────────────────────────────

const SCENE_DURATION_MS = 6000;

// ── Inner component (needs ReactFlowProvider wrapper) ───────────────────────

function FlowInner({ explanation, storyboard, activeSceneIndex }: PromptExplainerFlowProps) {
  const controlled = activeSceneIndex !== undefined;
  const [internalScene, setInternalScene] = useState(0);
  const [playing, setPlaying] = useState(false);
  const { fitView, setCenter } = useReactFlow();
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const currentScene = controlled ? activeSceneIndex : internalScene;
  const scene: PromptScene | undefined = storyboard.scenes[currentScene];

  // Compute dagre positions once
  const positions = useMemo(
    () => layoutParts(explanation.parts, explanation.relationships),
    [explanation],
  );

  // Build nodes for current scene
  const sceneNodes: Node[] = useMemo(() => {
    if (!scene) return [];
    const visible = new Set(scene.visible_parts);
    const highlighted = new Set(scene.highlighted_parts);
    const anyHighlighted = highlighted.size > 0;

    return explanation.parts.map((p) => {
      const pos = positions.get(p.id) ?? { x: 0, y: 0 };
      const isVisible = visible.has(p.id);
      const isHighlighted = highlighted.has(p.id);
      return {
        id: p.id,
        type: "part",
        position: pos,
        hidden: !isVisible,
        data: {
          label: p.label,
          kind: p.kind,
          description: p.description,
          highlighted: isHighlighted,
          dimmed: anyHighlighted && !isHighlighted && isVisible,
        },
      };
    });
  }, [explanation, scene, positions]);

  // Build edges for current scene
  const sceneEdges: Edge[] = useMemo(() => {
    if (!scene) return [];
    const highlightedRels = new Set(scene.highlighted_relationships);
    const visible = new Set(scene.visible_parts);

    return explanation.relationships
      .filter((r) => visible.has(r.from) && visible.has(r.to))
      .map((r) => {
        const isHighlighted = highlightedRels.has(r.id);
        return {
          id: r.id,
          source: r.from,
          target: r.to,
          label: r.label || undefined,
          animated: isHighlighted,
          style: {
            stroke: isHighlighted ? EDGE_COLOR_ACTIVE : EDGE_COLOR_DIM,
            strokeWidth: isHighlighted ? 2.5 : 1.5,
            transition: "all 0.5s ease",
          },
          labelStyle: {
            fontSize: 10,
            fill: isHighlighted ? "#fff" : "#ffffff60",
          },
          labelShowBg: true,
          labelBgStyle: {
            fill: "#0a0a0f",
            fillOpacity: 0.85,
            rx: 4,
            ry: 4,
          },
          labelBgPadding: [4, 2] as [number, number],
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: isHighlighted ? EDGE_COLOR_ACTIVE : EDGE_COLOR_DIM,
          },
        };
      });
  }, [explanation, scene]);

  const [nodes, setNodes, onNodesChange] = useNodesState(sceneNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(sceneEdges);

  // Update nodes/edges when scene changes
  useEffect(() => {
    setNodes(sceneNodes);
    setEdges(sceneEdges);
  }, [sceneNodes, sceneEdges, setNodes, setEdges]);

  // Camera: fit view or focus on part
  useEffect(() => {
    if (!scene) return;

    const applyCamera = () => {
      if (scene.camera_mode === "focus" && scene.focus_part) {
        const pos = positions.get(scene.focus_part);
        if (pos) {
          setCenter(pos.x + NODE_WIDTH / 2, pos.y + NODE_HEIGHT / 2, { zoom: 1.4, duration: 600 });
          return;
        }
      }
      fitView({ padding: 0.25, duration: 600 });
    };

    const t1 = setTimeout(applyCamera, 80);
    const t2 = setTimeout(applyCamera, 420);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, [currentScene, scene, fitView, setCenter, positions]);

  // Auto-play timer (only when self-managed)
  useEffect(() => {
    if (controlled || !playing) return;
    timerRef.current = setInterval(() => {
      setInternalScene((prev) => {
        if (prev >= storyboard.scenes.length - 1) {
          setPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, SCENE_DURATION_MS);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [controlled, playing, storyboard.scenes.length]);

  const handlePrev = useCallback(() => setInternalScene((p) => Math.max(0, p - 1)), []);
  const handleNext = useCallback(
    () => setInternalScene((p) => Math.min(storyboard.scenes.length - 1, p + 1)),
    [storyboard.scenes.length],
  );
  const handleTogglePlay = useCallback(() => setPlaying((p) => !p), []);

  if (!scene) {
    return <div className="flex h-full items-center justify-center text-white/40">No scenes</div>;
  }

  return (
    <div className="flex h-full w-full gap-4">
      {/* React Flow canvas */}
      <div className="relative flex-1 rounded-xl overflow-hidden border border-white/10">
        {/* Title */}
        <div className="absolute left-4 top-4 z-10 rounded-lg bg-black/60 backdrop-blur-md px-3 py-1.5">
          <span className="text-xs text-white/50">{explanation.explanation_type.replace("_", " ")}</span>
          <h2 className="text-sm font-bold text-white">{explanation.title}</h2>
        </div>

        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          proOptions={{ hideAttribution: true }}
          minZoom={0.3}
          maxZoom={2}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
          panOnDrag
          zoomOnScroll
          className="bg-gray-950"
        >
          <Background color="#ffffff10" gap={20} />
        </ReactFlow>

        {/* Scene controls overlay at bottom (only when self-managed) */}
        {!controlled && (
          <div className="absolute bottom-4 left-1/2 z-10 -translate-x-1/2">
            <div className="flex items-center gap-3 rounded-xl bg-black/80 backdrop-blur-md px-4 py-2 border border-white/10 shadow-lg">
              <button
                onClick={handlePrev}
                disabled={currentScene === 0}
                className="rounded px-2 py-1 text-xs text-white/60 hover:bg-white/10 disabled:opacity-30 transition-colors"
              >
                ← Prev
              </button>
              <span className="text-[10px] text-white/40 font-semibold uppercase tracking-wider">
                {currentScene + 1} / {storyboard.scenes.length}
              </span>
              <button
                onClick={handleTogglePlay}
                className="rounded px-2 py-1 text-xs text-white/60 hover:bg-white/10 transition-colors"
              >
                {playing ? "⏸" : "▶"}
              </button>
              <button
                onClick={handleNext}
                disabled={currentScene === storyboard.scenes.length - 1}
                className="rounded px-2 py-1 text-xs text-white/60 hover:bg-white/10 disabled:opacity-30 transition-colors"
              >
                Next →
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Side info panel (only when self-managed) */}
      {!controlled && (
        <div className="w-72 shrink-0 overflow-y-auto rounded-xl border border-white/10 bg-black/30 backdrop-blur-md p-4">
          <h3 className="text-sm font-bold text-white">{scene.title}</h3>
          {scene.goal && <p className="mt-1 text-[11px] text-blue-300/70">{scene.goal}</p>}
          {scene.narration && (
            <p className="mt-3 text-xs leading-relaxed text-white/60">{scene.narration}</p>
          )}
          {scene.panel && (
            <div className="mt-4">
              {scene.panel.title && (
                <h4 className="text-[11px] font-semibold text-white/80 uppercase tracking-wider mb-1">
                  {scene.panel.title}
                </h4>
              )}
              <ul className="space-y-1">
                {scene.panel.bullets.map((b, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-[11px] text-white/50">
                    <span className="mt-0.5 text-blue-400">•</span>
                    {b}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Exported wrapper with ReactFlowProvider ─────────────────────────────────

export default function PromptExplainerFlow(props: PromptExplainerFlowProps) {
  return (
    <ReactFlowProvider>
      <FlowInner {...props} />
    </ReactFlowProvider>
  );
}
