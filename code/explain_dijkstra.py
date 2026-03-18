from manim import *


class DijkstraScene(Scene):
    def construct(self):
        # Graph definition
        # Nodes: A, B, C, D, E, F
        # Edges with weights
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

        node_positions = {
            "A": LEFT * 4,
            "B": LEFT * 2 + UP * 2,
            "C": LEFT * 2 + DOWN * 1,
            "D": RIGHT * 0.5 + UP * 2,
            "E": RIGHT * 0.5 + DOWN * 1,
            "F": RIGHT * 3,
        }

        colors = {
            "default": BLUE_D,
            "visited": GREEN_D,
            "current": YELLOW,
            "path": ORANGE,
        }

        # --- Build graph visuals ---
        node_circles = {}
        node_labels = {}
        for name in NODES:
            pos = node_positions[name]
            circle = Circle(radius=0.35, color=colors["default"], fill_opacity=0.8)
            circle.move_to(pos)
            label = Text(name, font_size=22, color=WHITE, weight=BOLD)
            label.move_to(pos)
            node_circles[name] = circle
            node_labels[name] = label

        edge_lines = {}
        edge_weight_labels = {}
        for u, v, w in EDGES:
            start = node_positions[u]
            end = node_positions[v]
            line = Line(start, end, color=GRAY, stroke_width=2)
            mid = (start + end) / 2
            offset = normalize(rotate_vector(end - start, PI / 2)) * 0.25
            wlabel = Text(str(w), font_size=18, color=LIGHT_GRAY)
            wlabel.move_to(mid + offset)
            edge_lines[(u, v)] = line
            edge_weight_labels[(u, v)] = wlabel

        # --- Distance table (top right) ---
        def make_dist_table(distances):
            rows = [["Node", "Dist"]] + [
                [n, str(distances[n]) if distances[n] < float("inf") else "∞"]
                for n in NODES
            ]
            table = Table(
                [row[1:] for row in rows[1:]],
                row_labels=[Text(r[0], font_size=16) for r in rows[1:]],
                col_labels=[Text("Dist", font_size=16)],
                include_outer_lines=True,
                line_config={"stroke_width": 1, "color": GRAY},
                element_to_mobject=lambda el: Text(el, font_size=16),
            )
            table.scale(0.55)
            table.to_corner(UR, buff=0.3)
            return table

        # --- Title ---
        title = Text("Dijkstra's Algorithm", font_size=30, color=WHITE)
        title.to_corner(UL, buff=0.3)

        # --- Animate graph construction ---
        self.play(Write(title))
        self.play(
            *[Create(line) for line in edge_lines.values()],
            *[Write(wl) for wl in edge_weight_labels.values()],
            run_time=1.5,
        )
        self.play(
            *[DrawBorderThenFill(c) for c in node_circles.values()],
            *[Write(l) for l in node_labels.values()],
            run_time=1.5,
        )

        # Initial distances
        INF = float("inf")
        distances = {n: INF for n in NODES}
        distances["A"] = 0
        previous = {n: None for n in NODES}

        dist_table = make_dist_table(distances)
        self.play(Create(dist_table))
        self.wait(0.5)

        # --- Step label ---
        step_label = Text("Start: A  |  dist[A] = 0", font_size=20, color=YELLOW)
        step_label.to_edge(DOWN, buff=0.3)
        self.play(Write(step_label))
        self.wait(0.5)

        # Adjacency list
        adj = {n: [] for n in NODES}
        for u, v, w in EDGES:
            adj[u].append((v, w))
            adj[v].append((u, w))

        visited = set()
        unvisited = set(NODES)

        # --- Dijkstra steps ---
        steps = [
            ("A", "B", 4, "Visit A → relax B (0+4=4), C (0+2=2)"),
            ("A", "C", 2, "Visit A → relax B (0+4=4), C (0+2=2)"),
            ("C", "B", 3, "Visit C (dist=2) → relax B: 2+1=3 < 4"),
            ("C", "E", 12, "Visit C → relax E: 2+10=12"),
            ("B", "D", 8, "Visit B (dist=3) → relax D: 3+5=8"),
            ("D", "F", 10, "Visit D (dist=8) → relax F: 8+2=10"),
            ("E", "F", 10, "Visit E (dist=12) → F already 10, no update"),
        ]

        # Run actual Dijkstra to animate
        dijkstra_order = []
        dist_snap = {n: INF for n in NODES}
        dist_snap["A"] = 0
        prev_snap = {n: None for n in NODES}

        unvisited2 = set(NODES)
        while unvisited2:
            current = min(unvisited2, key=lambda x: dist_snap[x])
            if dist_snap[current] == INF:
                break
            dijkstra_order.append((current, dict(dist_snap), dict(prev_snap)))
            unvisited2.remove(current)
            for neighbor, weight in adj[current]:
                if neighbor in unvisited2:
                    new_dist = dist_snap[current] + weight
                    if new_dist < dist_snap[neighbor]:
                        dist_snap[neighbor] = new_dist
                        prev_snap[neighbor] = current

        # Animate each step
        visited_nodes = set()
        for i, (current, dists, prevs) in enumerate(dijkstra_order):
            # Highlight current node
            self.play(
                node_circles[current].animate.set_color(colors["current"]),
                run_time=0.4,
            )

            step_text = Text(
                f"Step {i+1}: Visit {current}  (dist = {dists[current]})",
                font_size=20,
                color=YELLOW,
            )
            step_text.to_edge(DOWN, buff=0.3)
            self.play(Transform(step_label, step_text), run_time=0.3)

            # Relax neighbors
            for neighbor, weight in adj[current]:
                new_d = dists[current] + weight
                if new_d <= dists.get(neighbor, INF):
                    key = (current, neighbor) if (current, neighbor) in edge_lines else (neighbor, current)
                    if key in edge_lines:
                        self.play(
                            edge_lines[key].animate.set_color(YELLOW).set_stroke(width=4),
                            run_time=0.3,
                        )

            # Mark visited
            visited_nodes.add(current)
            self.play(
                node_circles[current].animate.set_color(colors["visited"]),
                run_time=0.3,
            )

            # Update table
            new_table = make_dist_table(dists)
            self.play(Transform(dist_table, new_table), run_time=0.4)
            self.wait(0.3)

        # --- Highlight shortest path A → F ---
        path_label = Text("Shortest path: A → C → B → D → F  (cost: 10)", font_size=20, color=ORANGE)
        path_label.to_edge(DOWN, buff=0.3)
        self.play(Transform(step_label, path_label))

        path_edges = [("A", "C"), ("C", "B"), ("B", "D"), ("D", "F")]
        path_nodes_order = ["A", "C", "B", "D", "F"]

        for u, v in path_edges:
            key = (u, v) if (u, v) in edge_lines else (v, u)
            self.play(
                edge_lines[key].animate.set_color(ORANGE).set_stroke(width=5),
                run_time=0.4,
            )
        for n in path_nodes_order:
            self.play(
                node_circles[n].animate.set_color(ORANGE),
                run_time=0.3,
            )

        self.wait(2)
