import os
from manim import *

# ---------------------------------------------------------------------------
# Shared graph data
# ---------------------------------------------------------------------------
NODES = ["A", "B", "C", "D", "E", "F"]
EDGES = [
    ("A", "B", 4),
    ("A", "C", 2),
    ("B", "C", 1),
    ("B", "D", 5),
    ("C", "D", 8),
    ("C", "E", 10),
    ("D", "F", 2),
    ("E", "F", 3),
]
# Layout kept within safe zone: x ∈ [-5.5, 5.5], y ∈ [-2.5, 2.5]
NODE_POSITIONS = {
    "A": LEFT * 3.5,
    "B": LEFT * 1.5 + UP * 1.8,
    "C": LEFT * 1.5 + DOWN * 0.9,
    "D": RIGHT * 0.8 + UP * 1.8,
    "E": RIGHT * 0.8 + DOWN * 0.9,
    "F": RIGHT * 3.0,
}
C_DEFAULT = BLUE_D
C_VISITED = GREEN_D
C_CURRENT = YELLOW
C_PATH    = ORANGE

# Timing injected by the pipeline so animations pace with the TTS narration.
STEP_TIME   = float(os.environ.get("MANIM_STEP_TIME",   "2.0"))
INTRO_WAIT  = float(os.environ.get("MANIM_INTRO_WAIT",  "2.5"))
OUTRO_WAIT  = float(os.environ.get("MANIM_OUTRO_WAIT",  "3.0"))


def _build_graph():
    """Return (node_circles, node_labels, edge_lines, edge_weight_labels)."""
    node_circles, node_labels = {}, {}
    for name in NODES:
        pos = NODE_POSITIONS[name]
        circle = Circle(radius=0.32, color=C_DEFAULT, fill_opacity=0.85)
        circle.move_to(pos)
        label = Text(name, font_size=20, color=WHITE, weight=BOLD)
        label.move_to(pos)
        node_circles[name] = circle
        node_labels[name]   = label

    edge_lines, edge_weight_labels = {}, {}
    for u, v, w in EDGES:
        start, end = NODE_POSITIONS[u], NODE_POSITIONS[v]
        line = Line(start, end, color=GRAY, stroke_width=2)
        mid  = (start + end) / 2
        off  = normalize(rotate_vector(end - start, PI / 2)) * 0.22
        wlbl = Text(str(w), font_size=16, color=LIGHT_GRAY)
        wlbl.move_to(mid + off)
        edge_lines[(u, v)]         = line
        edge_weight_labels[(u, v)] = wlbl

    return node_circles, node_labels, edge_lines, edge_weight_labels


def _make_dist_table(distances):
    """Small distance table; positioned right side, within safe zone."""
    table = Table(
        [[str(distances[n]) if distances[n] < float("inf") else "∞"] for n in NODES],
        row_labels=[Text(n, font_size=14) for n in NODES],
        col_labels=[Text("dist", font_size=14)],
        include_outer_lines=True,
        line_config={"stroke_width": 1, "color": GRAY},
        element_to_mobject=lambda el: Text(el, font_size=14),
    )
    table.scale(0.48)
    # Anchor to right edge, vertically centred
    table.move_to(RIGHT * 5.5)
    return table


def _run_dijkstra():
    """Return list of (current, dist_snapshot, prev_snapshot) visit order."""
    INF = float("inf")
    dist = {n: INF for n in NODES}
    dist["A"] = 0
    prev = {n: None for n in NODES}
    adj  = {n: [] for n in NODES}
    for u, v, w in EDGES:
        adj[u].append((v, w))
        adj[v].append((u, w))
    order, unvisited = [], set(NODES)
    while unvisited:
        cur = min(unvisited, key=lambda x: dist[x])
        if dist[cur] == float("inf"):
            break
        order.append((cur, dict(dist), dict(prev)))
        unvisited.remove(cur)
        for nb, wt in adj[cur]:
            if nb in unvisited and dist[cur] + wt < dist[nb]:
                dist[nb] = dist[cur] + wt
                prev[nb] = cur
    return order, adj


# ---------------------------------------------------------------------------
# Scene 1 — Intro: build the graph and explain the problem
# ---------------------------------------------------------------------------
class DijkstraIntro(Scene):
    def construct(self):
        title = Text("Dijkstra's Algorithm", font_size=32, color=WHITE)
        title.move_to(UP * 3.2)

        subtitle = Text(
            "Shortest path in a weighted graph",
            font_size=20, color=GRAY,
        )
        subtitle.next_to(title, DOWN, buff=0.2)

        nc, nl, el, ewl = _build_graph()

        # Goal label
        goal = Text("Goal: shortest path  A → F", font_size=18, color=YELLOW)
        goal.move_to(DOWN * 3.2)

        self.play(Write(title), run_time=1.0)
        self.play(FadeIn(subtitle), run_time=0.6)
        self.wait(INTRO_WAIT * 0.3)

        self.play(
            *[Create(l)  for l in el.values()],
            *[Write(wl)  for wl in ewl.values()],
            run_time=2.0,
        )
        self.play(
            *[DrawBorderThenFill(c) for c in nc.values()],
            *[Write(lb)             for lb in nl.values()],
            run_time=1.5,
        )
        self.wait(INTRO_WAIT * 0.4)

        self.play(Write(goal), run_time=0.8)
        self.wait(INTRO_WAIT)


# ---------------------------------------------------------------------------
# Scene 2 — Steps: step-by-step Dijkstra execution
# ---------------------------------------------------------------------------
class DijkstraSteps(Scene):
    def construct(self):
        title = Text("Dijkstra's Algorithm — Execution", font_size=24, color=WHITE)
        title.move_to(UP * 3.2)
        self.play(Write(title), run_time=0.8)

        nc, nl, el, ewl = _build_graph()

        INF = float("inf")
        dist_init = {n: INF for n in NODES}
        dist_init["A"] = 0

        dist_table = _make_dist_table(dist_init)

        # Show graph + initial table
        self.play(
            *[Create(l)  for l in el.values()],
            *[Write(wl)  for wl in ewl.values()],
            run_time=1.5,
        )
        self.play(
            *[DrawBorderThenFill(c) for c in nc.values()],
            *[Write(lb)             for lb in nl.values()],
            run_time=1.2,
        )
        self.play(Create(dist_table), run_time=0.8)

        step_label = Text("Start: dist[A] = 0, all others = ∞", font_size=17, color=YELLOW)
        step_label.move_to(DOWN * 3.2)
        self.play(Write(step_label), run_time=0.6)
        self.wait(STEP_TIME * 0.6)

        dijkstra_order, adj = _run_dijkstra()

        for i, (current, dists, _) in enumerate(dijkstra_order):
            # Highlight current node
            self.play(nc[current].animate.set_color(C_CURRENT), run_time=0.6)

            new_lbl = Text(
                f"Step {i+1}: Visit {current}  (dist = {dists[current]})",
                font_size=17, color=YELLOW,
            )
            new_lbl.move_to(DOWN * 3.2)
            self.play(Transform(step_label, new_lbl), run_time=0.5)
            self.wait(STEP_TIME * 0.4)

            # Relax edges
            for nb, wt in adj[current]:
                new_d = dists[current] + wt
                if new_d <= dists.get(nb, INF):
                    key = (current, nb) if (current, nb) in el else (nb, current)
                    if key in el:
                        self.play(
                            el[key].animate.set_color(YELLOW).set_stroke(width=3),
                            run_time=0.5,
                        )
                        self.wait(STEP_TIME * 0.25)

            # Mark visited
            self.play(nc[current].animate.set_color(C_VISITED), run_time=0.5)

            # Update distance table
            new_table = _make_dist_table(dists)
            self.play(Transform(dist_table, new_table), run_time=0.6)
            self.wait(STEP_TIME * 0.5)

        done_lbl = Text("All nodes visited — done!", font_size=17, color=GREEN)
        done_lbl.move_to(DOWN * 3.2)
        self.play(Transform(step_label, done_lbl), run_time=0.5)
        self.wait(STEP_TIME * 0.4)


# ---------------------------------------------------------------------------
# Scene 3 — Outro: global view — full graph + optimal path highlighted
# ---------------------------------------------------------------------------
class DijkstraOutro(Scene):
    def construct(self):
        title = Text("Shortest Path Found", font_size=32, color=WHITE)
        title.move_to(UP * 3.2)
        self.play(Write(title), run_time=0.8)

        nc, nl, el, ewl = _build_graph()

        # Show all nodes as visited (green)
        for c in nc.values():
            c.set_color(C_VISITED)

        self.play(
            *[Create(l)  for l in el.values()],
            *[Write(wl)  for wl in ewl.values()],
            run_time=1.5,
        )
        self.play(
            *[DrawBorderThenFill(c) for c in nc.values()],
            *[Write(lb)             for lb in nl.values()],
            run_time=1.0,
        )
        self.wait(OUTRO_WAIT * 0.2)

        # Final distances summary (static table)
        final_dists = {"A": 0, "B": 3, "C": 2, "D": 8, "E": 12, "F": 10}
        final_table = _make_dist_table(final_dists)
        self.play(Create(final_table), run_time=0.8)
        self.wait(OUTRO_WAIT * 0.3)

        # Highlight optimal path  A → C → B → D → F
        path_edges  = [("A", "C"), ("C", "B"), ("B", "D"), ("D", "F")]
        path_nodes  = ["A", "C", "B", "D", "F"]

        path_lbl = Text("A → C → B → D → F  (cost: 10)", font_size=20, color=ORANGE)
        path_lbl.move_to(DOWN * 3.2)
        self.play(Write(path_lbl), run_time=0.7)

        for u, v in path_edges:
            key = (u, v) if (u, v) in el else (v, u)
            self.play(
                el[key].animate.set_color(ORANGE).set_stroke(width=5),
                run_time=0.6,
            )
            self.wait(0.3)

        self.play(
            *[nc[n].animate.set_color(ORANGE) for n in path_nodes],
            run_time=0.7,
        )
        self.wait(OUTRO_WAIT * 0.5)

        # Summary text
        summary = VGroup(
            Text("Greedy: always expand the nearest unvisited node", font_size=15, color=LIGHT_GRAY),
            Text("Works on non-negative weights · O((V+E) log V)", font_size=15, color=LIGHT_GRAY),
        ).arrange(DOWN, buff=0.2)
        summary.move_to(UP * 0.6 + RIGHT * 2.0)

        self.play(FadeIn(summary), run_time=1.0)
        self.wait(OUTRO_WAIT)
