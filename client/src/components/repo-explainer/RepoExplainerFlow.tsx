/**
 * Main React Flow renderer for repo architecture explanation.
 *
 * Takes architecture + storyboard JSON and renders an interactive
 * scene-driven walkthrough using React Flow.
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

import ComponentNode from "./ComponentNode";
import SceneControls from "./SceneControls";
import InfoPanel from "./InfoPanel";

// ── Types matching backend repo_models ──────────────────────────────────────

interface ArchComponent {
  id: string;
  label: string;
  type: string;
  paths: string[];
  responsibility: string;
}

interface ArchRelationship {
  id: string;
  from: string;
  to: string;
  kind: string;
  label: string;
}

interface Architecture {
  repo_name: string;
  summary: string;
  components: ArchComponent[];
  relationships: ArchRelationship[];
  flows: { id: string; title: string; steps: string[] }[];
}

interface ScenePanel {
  title: string;
  bullets: string[];
}

interface Scene {
  id: string;
  title: string;
  goal: string;
  visible_components: string[];
  highlighted_components: string[];
  highlighted_relationships: string[];
  camera_mode: string;
  focus_component: string | null;
  narration: string;
  panel: ScenePanel | null;
}

interface Storyboard {
  scenes: Scene[];
}

interface RepoExplainerFlowProps {
  architecture: Architecture;
  storyboard: Storyboard;
  /** When provided, scene is controlled externally (by RepoPlayer). */
  activeSceneIndex?: number;
}

// ── Dagre layout ────────────────────────────────────────────────────────────

const NODE_WIDTH = 220;
const NODE_HEIGHT = 120;

function layoutNodes(
  components: ArchComponent[],
  relationships: ArchRelationship[],
): Map<string, { x: number; y: number }> {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", ranksep: 140, nodesep: 80 });

  components.forEach((c) => {
    g.setNode(c.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });
  relationships.forEach((r) => {
    if (g.hasNode(r.from) && g.hasNode(r.to)) {
      g.setEdge(r.from, r.to);
    }
  });

  dagre.layout(g);

  const positions = new Map<string, { x: number; y: number }>();
  components.forEach((c) => {
    const node = g.node(c.id);
    if (node) {
      positions.set(c.id, { x: node.x - NODE_WIDTH / 2, y: node.y - NODE_HEIGHT / 2 });
    }
  });
  return positions;
}

// ── Edge style by kind ──────────────────────────────────────────────────────

const EDGE_COLORS: Record<string, string> = {
  http: "#60a5fa",
  calls: "#a78bfa",
  imports: "#6ee7b7",
  emits: "#fbbf24",
  reads: "#fb923c",
  writes: "#f87171",
};

// ── Node types ──────────────────────────────────────────────────────────────

const nodeTypes = { component: ComponentNode };

// ── Auto-play interval ──────────────────────────────────────────────────────

const SCENE_DURATION_MS = 6000;

// ── Inner component (needs ReactFlowProvider wrapper) ───────────────────────

function FlowInner({ architecture, storyboard, activeSceneIndex }: RepoExplainerFlowProps) {
  const controlled = activeSceneIndex !== undefined;
  const [internalScene, setInternalScene] = useState(0);
  const [playing, setPlaying] = useState(false);
  const { fitView, setCenter } = useReactFlow();
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const currentScene = controlled ? activeSceneIndex : internalScene;
  const scene: Scene | undefined = storyboard.scenes[currentScene];

  // Compute dagre positions once
  const positions = useMemo(
    () => layoutNodes(architecture.components, architecture.relationships),
    [architecture],
  );

  // Build nodes for current scene
  const sceneNodes: Node[] = useMemo(() => {
    if (!scene) return [];
    const visible = new Set(scene.visible_components);
    const highlighted = new Set(scene.highlighted_components);
    const anyHighlighted = highlighted.size > 0;

    return architecture.components.map((c) => {
      const pos = positions.get(c.id) ?? { x: 0, y: 0 };
      const isVisible = visible.has(c.id);
      const isHighlighted = highlighted.has(c.id);
      return {
        id: c.id,
        type: "component",
        position: pos,
        hidden: !isVisible,
        data: {
          label: c.label,
          type: c.type,
          responsibility: c.responsibility,
          highlighted: isHighlighted,
          dimmed: anyHighlighted && !isHighlighted && isVisible,
        },
      };
    });
  }, [architecture, scene, positions]);

  // Build edges for current scene
  const sceneEdges: Edge[] = useMemo(() => {
    if (!scene) return [];
    const highlightedRels = new Set(scene.highlighted_relationships);
    const visible = new Set(scene.visible_components);

    return architecture.relationships
      .filter((r) => visible.has(r.from) && visible.has(r.to))
      .map((r) => {
        const isHighlighted = highlightedRels.has(r.id);
        const color = EDGE_COLORS[r.kind] || "#94a3b8";
        return {
          id: r.id,
          source: r.from,
          target: r.to,
          label: r.label || undefined,
          animated: isHighlighted,
          style: {
            stroke: isHighlighted ? color : `${color}40`,
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
            color: isHighlighted ? color : `${color}40`,
          },
        };
      });
  }, [architecture, scene]);

  const [nodes, setNodes, onNodesChange] = useNodesState(sceneNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(sceneEdges);

  // Update nodes/edges when scene changes
  useEffect(() => {
    setNodes(sceneNodes);
    setEdges(sceneEdges);
  }, [sceneNodes, sceneEdges, setNodes, setEdges]);

  // Camera: fit view or focus on component
  // Double-trigger: quick first pass (50ms) + accurate pass after full render (400ms)
  useEffect(() => {
    if (!scene) return;

    const applyCamera = () => {
      if (scene.camera_mode === "focus" && scene.focus_component) {
        const pos = positions.get(scene.focus_component);
        if (pos) {
          setCenter(pos.x + NODE_WIDTH / 2, pos.y + NODE_HEIGHT / 2, { zoom: 1.4, duration: 600 });
          return;
        }
      }
      fitView({ padding: 0.25, duration: 600 });
    };

    const t1 = setTimeout(applyCamera, 80);
    const t2 = setTimeout(applyCamera, 420);   // second pass after ReactFlow finishes layout
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
        {/* Repo title */}
        <div className="absolute left-4 top-4 z-10 rounded-lg bg-black/60 backdrop-blur-md px-3 py-1.5">
          <span className="text-xs text-white/50">Repository</span>
          <h2 className="text-sm font-bold text-white">{architecture.repo_name}</h2>
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
            <SceneControls
              currentScene={currentScene}
              totalScenes={storyboard.scenes.length}
              sceneTitle={scene.title}
              onPrev={handlePrev}
              onNext={handleNext}
              playing={playing}
              onTogglePlay={handleTogglePlay}
            />
          </div>
        )}
      </div>

      {/* Side info panel (only when self-managed) */}
      {!controlled && (
        <div className="w-72 shrink-0">
          <InfoPanel
            sceneTitle={scene.title}
            goal={scene.goal}
            narration={scene.narration}
            panel={scene.panel}
          />
        </div>
      )}
    </div>
  );
}

// ── Exported wrapper with ReactFlowProvider ─────────────────────────────────

export default function RepoExplainerFlow(props: RepoExplainerFlowProps) {
  return (
    <ReactFlowProvider>
      <FlowInner {...props} />
    </ReactFlowProvider>
  );
}
