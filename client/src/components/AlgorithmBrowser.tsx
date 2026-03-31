import { useState, useMemo } from "react";
import { Search, X, Play } from "lucide-react";

export interface AlgorithmItem {
  id: string;
  label: string;
  category: string;
  file: string;
}

const allAlgorithms: AlgorithmItem[] = [
  // Sorting
  { id: "bubble_sort", label: "Bubble Sort", category: "Sorting", file: "/demo/bubble_sort.mp4" },
  { id: "heap_sort", label: "Heap Sort", category: "Sorting", file: "/demo/heap_sort.mp4" },
  { id: "insertion_sort", label: "Insertion Sort", category: "Sorting", file: "/demo/insertion_sort.mp4" },
  { id: "merge_sort", label: "Merge Sort", category: "Sorting", file: "/demo/merge_sort.mp4" },
  { id: "quick_sort", label: "Quick Sort", category: "Sorting", file: "/demo/quick_sort.mp4" },
  { id: "radix_sort", label: "Radix Sort", category: "Sorting", file: "/demo/radix_sort.mp4" },
  { id: "selection_sort", label: "Selection Sort", category: "Sorting", file: "/demo/selection_sort.mp4" },

  // Searching
  { id: "binary_search", label: "Binary Search", category: "Searching", file: "/demo/binary_search.mp4" },
  { id: "bfs", label: "Breadth-First Search (BFS)", category: "Searching", file: "/demo/bfs.mp4" },
  { id: "dfs", label: "Depth-First Search (DFS)", category: "Searching", file: "/demo/dfs.mp4" },
  { id: "linear_search", label: "Linear Search", category: "Searching", file: "/demo/linear_search.mp4" },

  // Graph Algorithms
  { id: "dijkstra", label: "Dijkstra's Algorithm", category: "Graph Algorithms", file: "/demo/dijkstra.mp4" },
  { id: "a_star", label: "A* Search", category: "Graph Algorithms", file: "/demo/a_star.mp4" },
  { id: "bellman_ford", label: "Bellman-Ford", category: "Graph Algorithms", file: "/demo/bellman_ford.mp4" },
  { id: "kruskal", label: "Kruskal's Algorithm", category: "Graph Algorithms", file: "/demo/kruskal.mp4" },
  { id: "prim", label: "Prim's Algorithm", category: "Graph Algorithms", file: "/demo/prim.mp4" },
  { id: "topological_sort", label: "Topological Sort", category: "Graph Algorithms", file: "/demo/topological_sort.mp4" },

  // Dynamic Programming
  { id: "fibonacci_dp", label: "Fibonacci (DP)", category: "Dynamic Programming", file: "/demo/fibonacci_dp.mp4" },
  { id: "knapsack", label: "Knapsack Problem", category: "Dynamic Programming", file: "/demo/knapsack.mp4" },
  { id: "lcs", label: "Longest Common Subsequence", category: "Dynamic Programming", file: "/demo/lcs.mp4" },
  { id: "lis", label: "Longest Increasing Subsequence", category: "Dynamic Programming", file: "/demo/lis.mp4" },

  // Data Structures
  { id: "binary_tree", label: "Binary Tree Traversal", category: "Data Structures", file: "/demo/binary_tree.mp4" },
  { id: "hash_table", label: "Hash Table", category: "Data Structures", file: "/demo/hash_table.mp4" },
  { id: "linked_list", label: "Linked List", category: "Data Structures", file: "/demo/linked_list.mp4" },
  { id: "stack_queue", label: "Stack & Queue", category: "Data Structures", file: "/demo/stack_queue.mp4" },

  // Core Concepts
  { id: "recursion", label: "Recursion", category: "Core Concepts", file: "/demo/recursion.mp4" },
  { id: "big_o", label: "Big O Notation", category: "Core Concepts", file: "/demo/big_o.mp4" },
  { id: "divide_conquer", label: "Divide & Conquer", category: "Core Concepts", file: "/demo/divide_conquer.mp4" },
  { id: "gradient_descent", label: "Gradient Descent", category: "Core Concepts", file: "/demo/gradient_descent.mp4" },
  { id: "tcp_handshake", label: "TCP Handshake", category: "Networking", file: "/demo/tcp_handshake.mp4" },

  // Networking
  { id: "dns_resolution", label: "DNS Resolution", category: "Networking", file: "/demo/dns_resolution.mp4" },
  { id: "http_lifecycle", label: "HTTP Request Lifecycle", category: "Networking", file: "/demo/http_lifecycle.mp4" },
];

const categoryOrder = [
  "Sorting",
  "Searching",
  "Graph Algorithms",
  "Dynamic Programming",
  "Data Structures",
  "Core Concepts",
  "Networking",
];

interface AlgorithmBrowserProps {
  open: boolean;
  onClose: () => void;
  onSelect: (item: AlgorithmItem) => void;
}

export default function AlgorithmBrowser({ open, onClose, onSelect }: AlgorithmBrowserProps) {
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim();
    if (!q) return allAlgorithms;
    return allAlgorithms.filter(
      (a) =>
        a.label.toLowerCase().includes(q) ||
        a.category.toLowerCase().includes(q)
    );
  }, [search]);

  const grouped = useMemo(() => {
    const map = new Map<string, AlgorithmItem[]>();
    for (const item of filtered) {
      const list = map.get(item.category) || [];
      list.push(item);
      map.set(item.category, list);
    }
    // Sort items alphabetically within each category
    for (const [, list] of map) {
      list.sort((a, b) => a.label.localeCompare(b.label));
    }
    // Return in fixed category order
    return categoryOrder
      .filter((cat) => map.has(cat))
      .map((cat) => ({ category: cat, items: map.get(cat)! }));
  }, [filtered]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div
        className="relative flex max-h-[80vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border bg-card shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 py-4">
          <h2 className="font-display text-lg font-bold">Browse All Topics</h2>
          <button
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Search */}
        <div className="border-b px-6 py-3">
          <div className="flex items-center gap-3 rounded-xl border bg-background px-4 py-2.5">
            <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
            <input
              autoFocus
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search algorithms, data structures, concepts…"
              className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
            {search && (
              <button onClick={() => setSearch("")} className="text-muted-foreground hover:text-foreground">
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Scrollable list */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {grouped.length === 0 && (
            <p className="py-12 text-center text-sm text-muted-foreground">
              No results for "{search}"
            </p>
          )}
          {grouped.map(({ category, items }) => (
            <div key={category} className="mb-6 last:mb-0">
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {category}
              </h3>
              <div className="grid gap-1.5">
                {items.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => {
                      onSelect(item);
                      onClose();
                    }}
                    className="group flex items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors hover:bg-accent/10"
                  >
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-secondary text-muted-foreground transition-colors group-hover:bg-accent group-hover:text-accent-foreground">
                      <Play className="h-3.5 w-3.5" />
                    </div>
                    <span className="text-sm font-medium">{item.label}</span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
