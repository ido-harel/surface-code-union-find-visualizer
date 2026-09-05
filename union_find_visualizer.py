import random
from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk

Vertex = tuple[int, int]
Edge = tuple[Vertex, Vertex]

def edge_key(a: Vertex, b: Vertex) -> Edge:
    return (a, b) if a < b else (b, a)

class UnionFind:
    def __init__(self, vertices: list[Vertex], syndrome: set[Vertex]):
        self.parent = {v: v for v in vertices}
        self.size = {v: 1 for v in vertices}
        self.parity = {v: int(v in syndrome) for v in vertices}

    def find(self, x: Vertex) -> Vertex:
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != x:
            x, self.parent[x] = self.parent[x], root
        return root

    def union(self, a: Vertex, b: Vertex) -> Vertex:
        a, b = self.find(a), self.find(b)
        if a == b:
            return a
        if self.size[a] < self.size[b]:
            a, b = b, a
        self.parent[b] = a
        self.size[a] += self.size[b]
        self.parity[a] ^= self.parity[b]
        return a


@dataclass
class StepResult:
    grown_halves: int
    merged: int
    odd_clusters: int


class DecoderModel:
    """Square-grid implementation of Algorithm 2's visible core."""

    def __init__(
        self,
        n: int = 11,
        p_z: float = 0.10,
        p_e: float = 0.08,
        seed=None,
    ):
        self.n, self.p_z, self.p_e = n, p_z, p_e
        self.rng = random.Random(seed)
        self.vertices = [(x, y) for y in range(n) for x in range(n)]
        self.edges: list[Edge] = []
        for y in range(n):
            for x in range(n):
                if x + 1 < n:
                    self.edges.append(edge_key((x, y), (x + 1, y)))
                if y + 1 < n:
                    self.edges.append(edge_key((x, y), (x, y + 1)))
        self.incident: dict[Vertex, list[Edge]] = {}
        for vertex in self.vertices:
            self.incident[vertex] = []

        for edge in self.edges:
            for vertex in edge:
                self.incident[vertex].append(edge)
        self.reset()

    def reset(self) -> None:
        self.errors = {e for e in self.edges if self.rng.random() < self.p_z}
        self.erasures = {e for e in self.edges if self.rng.random() < self.p_e}
        self.initialize_clusters()

    def initialize_clusters(self) -> None:
        self.syndrome: set[Vertex] = set()
        for v in self.vertices:
            if sum(e in self.errors for e in self.incident[v]) % 2:
                self.syndrome.add(v)
        self.uf = UnionFind(self.vertices, self.syndrome)
        self.halves: dict[tuple[Edge, Vertex], bool] = {
            (e, v): False for e in self.edges for v in e
        }
        # erased edge connected components are the initial clusters
        for e in self.erasures:
            self.halves[e, e[0]] = True
            self.halves[e, e[1]] = True
            self.uf.union(*e)
        self.round = 0
        self.pending_fusion = False
        self.finished = not self.odd_roots()

    def odd_roots(self) -> set[Vertex]:
        roots = {self.uf.find(v) for v in self.vertices}
        return {r for r in roots if self.uf.parity[self.uf.find(r)] == 1}

    def fully_grown(self, e: Edge) -> bool:
        return self.halves[e, e[0]] and self.halves[e, e[1]]

    def grow_step(self) -> StepResult:
        if self.finished:
            return StepResult(0, 0, 0)
       
        if self.pending_fusion:
            merged = 0
            for e in self.edges:
                if self.fully_grown(e) and self.uf.find(e[0]) != self.uf.find(e[1]):
                    self.uf.union(*e)
                    merged += 1
            self.pending_fusion = False
            self.round += 1
            odd = len(self.odd_roots())
            if odd == 0:
                self.finished = True
            return StepResult(0, merged, odd)

        active = self.odd_roots()
        additions: set[tuple[Edge, Vertex]] = set()

        for e in self.edges:
            a, b = e
            old_a, old_b = self.halves[e, a], self.halves[e, b]
            active_a = self.uf.find(a) in active
            active_b = self.uf.find(b) in active
            if not old_a and not old_b:
                # Each active endpoint gets to grow its half.
                if active_a:
                    additions.add((e, a))
                if active_b:
                    additions.add((e, b))
            elif old_a and not old_b and (active_a or active_b):
                additions.add((e, b))
            elif old_b and not old_a and (active_a or active_b):
                additions.add((e, a))
        for half in additions:
            self.halves[half] = True

        self.pending_fusion = any(
            self.fully_grown(e) and self.uf.find(e[0]) != self.uf.find(e[1])
            for e in self.edges
        )
        self.round += 1
        odd = len(self.odd_roots())
        if odd == 0 and not self.pending_fusion:
            self.finished = True
        return StepResult(len(additions), 0, odd)


PALETTE = ["#4e79a7", "#e07b73", "#59a14f", "#d4a72c", "#8064a2", "#76b7b2", "#af7a55"]


class DecoderApp:
    def __init__(self, root: tk.Tk, n: int, p_z: float, p_e: float, seed=None):
        self.root = root
        root.title("Union–Find Topological Decoder")
        root.geometry("1100x780")
        root.configure(bg="#f3f4f6")
        self.n_var = tk.IntVar(value=n)
        self.p_z_var = tk.DoubleVar(value=p_z)
        self.p_e_var = tk.DoubleVar(value=p_e)
        self.speed_var = tk.IntVar(value=550)
        self.seed = seed
        self.running = False
        self.after_id = None
        self.model = DecoderModel(n, p_z, p_e, seed)
        self._build()
        self.draw()

    def _build(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#f3f4f6")
        style.configure("TLabel", background="#f3f4f6", foreground="#202124")
        style.configure(
            "TButton", padding=7, background="#e2e5e9", foreground="#202124"
        )
        style.map("TButton", background=[("active", "#d2d6dc"), ("pressed", "#c5cad1")])
        style.configure("TSeparator", background="#c7ccd3")
        style.configure("TScale", background="#f3f4f6", troughcolor="#d7dbe0")
        style.configure("TSpinbox", fieldbackground="#ffffff", foreground="#202124")
        top = ttk.Frame(self.root, padding=12)
        top.pack(fill="x")
        ttk.Label(top, text="Grid").pack(side="left")
        ttk.Spinbox(
            top, from_=5, to=31, increment=2, width=4, textvariable=self.n_var
        ).pack(side="left", padx=5)
        ttk.Label(top, text="Syndrome probability p_z").pack(side="left", padx=(12, 0))
        ttk.Scale(
            top,
            from_=0.01,
            to=0.35,
            variable=self.p_z_var,
            length=130,
            command=lambda _x: self.p_z_text.config(text=f"{self.p_z_var.get():.3f}"),
        ).pack(side="left", padx=5)
        self.p_z_text = ttk.Label(top, text=f"{self.p_z_var.get():.3f}", width=6)
        self.p_z_text.pack(side="left")
        ttk.Label(top, text="Erasure probability p_e").pack(side="left", padx=(10, 0))
        ttk.Scale(
            top,
            from_=0.0,
            to=0.30,
            variable=self.p_e_var,
            length=100,
            command=lambda _x: self.p_e_text.config(
                text=f"{self.p_e_var.get():.3f}"
            ),
        ).pack(side="left", padx=5)
        self.p_e_text = ttk.Label(
            top, text=f"{self.p_e_var.get():.3f}", width=6
        )
        self.p_e_text.pack(side="left")
        ttk.Button(top, text="New sample", command=self.new_sample).pack(side="right")

        main = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        main.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(
            main, bg="#ffffff", highlightthickness=1, highlightbackground="#b8c0cc"
        )
        self.canvas.pack(side="left", fill="both", expand=True)
        side = ttk.Frame(main, padding=(16, 8), width=250)
        side.pack(side="right", fill="y")
        side.pack_propagate(False)
        ttk.Label(side, text="DECODER STATE", font=("Helvetica", 12, "bold")).pack(
            anchor="w", pady=(0, 8)
        )
        self.status = ttk.Label(side, text="", justify="left", font=("Menlo", 11))
        self.status.pack(anchor="w")
        ttk.Separator(side).pack(fill="x", pady=16)
        ttk.Button(side, text="▶  Run", command=self.toggle).pack(fill="x", pady=4)
        ttk.Button(side, text="→  One growth / fusion step", command=self.step).pack(
            fill="x", pady=4
        )
        ttk.Button(side, text="↻  Reset same errors", command=self.reset_same).pack(
            fill="x", pady=4
        )
        ttk.Label(side, text="Animation delay").pack(anchor="w", pady=(18, 0))
        ttk.Scale(side, from_=80, to=1200, variable=self.speed_var).pack(fill="x")
        ttk.Separator(side).pack(fill="x", pady=16)
        legend = [
            ("#6f42a1", "known erasure edge"),
            ("#d32f2f", "−1 syndrome vertex"),
            ("#d4a72c", "grown half-edge"),
        ]
        for color, label in legend:
            row = ttk.Frame(side)
            row.pack(fill="x", pady=3)
            tk.Label(
                row, text="●", fg=color, bg="#f3f4f6", font=("Helvetica", 14)
            ).pack(side="left")
            ttk.Label(row, text=label).pack(side="left", padx=7)
        ttk.Label(
            side,
            text=(
                "Clusters are colored. Only odd clusters grow; when two fronts "
                "complete an edge, Union merges them. Even clusters stop."
            ),
            wraplength=220,
            justify="left",
        ).pack(anchor="w", pady=(18, 0))
        self.canvas.bind("<Configure>", lambda _e: self.draw())

    def new_sample(self) -> None:
        self.stop()
        n = int(self.n_var.get())
        self.model = DecoderModel(
            n, float(self.p_z_var.get()), float(self.p_e_var.get()), self.seed
        )
        self.draw()

    def reset_same(self) -> None:
        errors = set(self.model.errors)
        erasures = set(self.model.erasures)
        self.stop()
        self.model.reset()
        self.model.errors = errors
        self.model.erasures = erasures
        self.model.initialize_clusters()
        self.draw()

    def stop(self) -> None:
        self.running = False
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def toggle(self) -> None:
        self.running = not self.running
        if self.running:
            self._tick()

    def _tick(self) -> None:
        if not self.running:
            return
        self.step()
        if self.model.finished:
            self.running = False
        else:
            self.after_id = self.root.after(int(self.speed_var.get()), self._tick)

    def step(self) -> None:
        self.model.grow_step()
        self.draw()

    def draw(self) -> None:
        c = self.canvas
        c.delete("all")
        w, h = max(c.winfo_width(), 500), max(c.winfo_height(), 500)
        margin = 45
        span = min(w, h) - 2 * margin
        gap = span / max(1, self.model.n - 1)
        ox = (w - span) / 2
        oy = (h - span) / 2
        point = lambda v: (ox + v[0] * gap, oy + v[1] * gap)
        roots = sorted({self.model.uf.find(v) for v in self.model.vertices})
        colors = {r: PALETTE[i % len(PALETTE)] for i, r in enumerate(roots)}
        # The actual Z-error chain is hidden: the decoder knows only its
        # syndrome and the explicitly erased locations.
        for e in self.model.edges:
            x1, y1 = point(e[0])
            x2, y2 = point(e[1])
            if e in self.model.erasures:
                color, width = "#6f42a1", 6
            else:
                color, width = "#d5d9df", 2
            c.create_line(x1, y1, x2, y2, fill=color, width=width)
        # Growth is drawn as half edges.
        for e in self.model.edges:
            x1, y1 = point(e[0])
            x2, y2 = point(e[1])
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            for v, end in ((e[0], (x1, y1)), (e[1], (x2, y2))):
                if self.model.halves[e, v]:
                    color = (
                        "#6f42a1"
                        if e in self.model.erasures
                        else colors[self.model.uf.find(v)]
                    )
                    c.create_line(end[0], end[1], mx, my, fill=color, width=6)
        radius = max(2.5, min(6, gap * 0.14))
        for v in self.model.vertices:
            x, y = point(v)
            root = self.model.uf.find(v)
            fill = "#d32f2f" if v in self.model.syndrome else "#202124"
            outline = "#ffffff"
            c.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill=fill,
                outline=outline,
                width=2,
            )
        phase = (
            "GROWTH COMPLETE"
            if self.model.finished
            else (
                "READY"
                if self.model.round == 0
                else ("FUSION NEXT" if self.model.pending_fusion else "GROWTH")
            )
        )
        isolated = sum(
            not any(e in self.model.erasures for e in self.model.incident[v])
            for v in self.model.syndrome
        )
        status_text = (
            f"phase       {phase}\n"
            f"round       {self.model.round}\n"
            f"erasures    {len(self.model.erasures)}\n"
            f"−1 vertices {len(self.model.syndrome)}\n"
            f"isolated −1 {isolated}\n"
            f"L size      {len(self.model.odd_roots())}"
        )
        self.status.config(text=status_text)


def main() -> None:
    root = tk.Tk()
    DecoderApp(root, n=11, p_z=0.10, p_e=0.08, seed=None)
    root.mainloop()


if __name__ == "__main__":
    main()
