"""Build paper figures from the selected presentation and matching saved episodes.

Run with Python, matplotlib, numpy, and Pillow installed.
All inputs needed for these figures are local to this folder.
"""
from pathlib import Path
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

ROOT = Path(__file__).resolve().parents[1] / "graph"
OUT = ROOT / "figures"
OUT.mkdir(exist_ok=True)
DATA = json.loads((ROOT / "figure_data.json").read_text())
INK = "#263544"
MUTED = "#526575"
BLUE = "#2370A8"
TEAL = "#168570"
GRAY = "#8393A1"
AMBER = "#AF6D12"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8.5,
    "axes.titlesize": 9, "axes.labelsize": 8.5,
    "xtick.labelsize": 8, "ytick.labelsize": 8,
    "text.color": INK, "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False,
    "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
})


def save(fig, name):
    for ext in ["pdf", "svg", "png"]:
        fig.savefig(OUT / f"{name}.{ext}", dpi=260,
                    bbox_inches="tight", pad_inches=0.035, facecolor="white")
    plt.close(fig)


def box(ax, x, y, w, h, title, body="", face="#F2F6FA", edge="#B7C6D2",
        title_color=INK, title_size=8.4, body_size=7.6):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.025,rounding_size=0.07",
                              facecolor=face, edgecolor=edge, linewidth=0.7))
    if body:
        ax.text(x+w/2, y+h*.72, title, ha="center", va="center",
                fontsize=title_size, fontweight="bold", color=title_color)
        ax.text(x+w/2, y+h*.31, body, ha="center", va="center",
                fontsize=body_size, linespacing=1.25)
    else:
        ax.text(x+w/2, y+h/2, title, ha="center", va="center",
                fontsize=title_size, linespacing=1.3, color=title_color)


def arrow(ax, points, color=MUTED, dashed=False):
    if len(points) > 2:
        xs, ys = zip(*points[:-1])
        ax.plot(xs, ys, color=color, lw=.85, linestyle="--" if dashed else "-",
                solid_capstyle="round")
    ax.add_patch(FancyArrowPatch(points[-2], points[-1], arrowstyle="-|>",
                                mutation_scale=8, lw=.85, color=color,
                                linestyle="--" if dashed else "-",
                                shrinkA=0, shrinkB=1.5))


def task_gallery():
    captions = [
        "Select items, pack, then cover.",
        "Choose objects and destinations.",
        "Sort using the user's rule.",
        "Reach the requested item counts.",
        "Open, retrieve, then close.",
        "Swap using a temporary pad.",
        "Search rooms and approach a target.",
        "Visit checkpoints and return.",
        "Uncover, inspect, then report.",
    ]
    fig = plt.figure(figsize=(6.6, 4.85))
    # Each image retains its original aspect ratio and complete content.
    for i, (name, caption) in enumerate(zip(DATA["task_names"], captions)):
        row, col = divmod(i, 3)
        left = .012 + col*.334
        bottom = .685 - row*.333
        fig.text(left+.158, bottom+.284, f"({chr(97+i)}) {name}",
                 ha="center", va="center", fontsize=8.4, fontweight="bold")
        ax = fig.add_axes([left, bottom+.045, .316, .227])
        ax.imshow(plt.imread(ROOT / "figure_assets" / f"task_{i+1:02}.png"))
        ax.set_axis_off()
        fig.text(left+.158, bottom+.018, caption, ha="center", va="center",
                 fontsize=7.1, color=MUTED)
    save(fig, "task_suite")


def benchmark_protocol():
    fig, ax = plt.subplots(figsize=(6.6, 3.65))
    ax.set(xlim=(-.06, 10.1), ylim=(0, 6.2))
    ax.axis("off")
    ax.text(.02, 6.02, "A. Construct and validate a task", fontsize=9, fontweight="bold")
    titles = ["Task template", "Physical scene", "User setup", "Validation"]
    bodies = ["Public dependencies", "Objects and initial poses", "Private choice + disclosure", "Scripted check; layout split"]
    for i, (title, body) in enumerate(zip(titles, bodies)):
        x = .02+2.57*i
        box(ax, x, 5.08, 2.16, .66, title, body, title_size=8, body_size=6.8)
        if i < 3:
            arrow(ax, [(x+2.19, 5.41), (x+2.52, 5.41)])
    ax.plot([.02, 9.92], [4.79, 4.79], color="#D8E1E7", lw=.8)
    ax.text(.02, 4.49, "B. Run the agent and evaluate the outcome", fontsize=9, fontweight="bold")

    box(ax, .02, 2.08, 1.93, 1.25, "Public state",
        "Instruction\nTask dependencies\nObservation + history", body_size=6.8)
    box(ax, 2.57, 2.31, 1.28, .79, "Gate", "ASK / CONTINUE", body_size=6.4)
    box(ax, 4.73, 3.23, 1.61, .77, "Question", "Language model", body_size=7)
    box(ax, 7.03, 3.23, 2.39, .77, "User answer",
        "Disclose requested choice", face="#FFF4DF", edge="#D9B572", body_size=7.1)
    box(ax, 4.73, 1.67, 1.61, .77, "Action", "Language model", body_size=7)
    box(ax, 7.03, 1.67, 2.39, .77, "PyBullet execution", "Fixed robot skills", body_size=7.1)
    box(ax, 7.03, .12, 2.39, .75, "Independent evaluator",
        "Final state + order + intent", face="#EAF6F1", edge="#80B5A5", body_size=7)

    arrow(ax, [(1.99, 2.71), (2.54, 2.71)])
    arrow(ax, [(3.9, 2.71), (4.26, 2.71), (4.26, 3.615), (4.69, 3.615)])
    arrow(ax, [(3.9, 2.71), (4.26, 2.71), (4.26, 2.055), (4.69, 2.055)])
    ax.text(4.15, 3.53, "ASK", fontsize=6.6, ha="right", color=AMBER)
    ax.text(4.18, 1.79, "CONTINUE", fontsize=6.4, ha="right", color=TEAL)
    arrow(ax, [(6.38, 3.615), (6.99, 3.615)])
    arrow(ax, [(6.38, 2.055), (6.99, 2.055)])
    arrow(ax, [(8.225, 4.04), (8.225, 4.22), (.985, 4.22), (.985, 3.37)])
    ax.text(3.76, 4.25, "Answer updates history", fontsize=6.6,
            ha="center", va="bottom", bbox={"facecolor":"white", "edgecolor":"none", "pad":1})
    arrow(ax, [(7.7, 1.63), (7.7, 1.2), (.985, 1.2), (.985, 2.04)])
    ax.text(3.65, 1.08, "Observation and action outcome", fontsize=6.6, ha="center", va="top")
    arrow(ax, [(8.75, 1.63), (8.75, .91)])
    ax.text(8.84, 1.23, "Task ends", fontsize=6.2, ha="left")
    ax.text(.02, .38, "Private user choices are excluded from the gate and planner input\nuntil disclosed in an answer or the initial instruction.",
            fontsize=7, color=MUTED, va="center", linespacing=1.3)
    fig.subplots_adjust(left=.0, right=1, bottom=.0, top=1)
    save(fig, "benchmark_protocol")


def clarification_examples():
    fig, ax = plt.subplots(figsize=(6.6, 2.72))
    ax.set(xlim=(-.06, 10.1), ylim=(0, 4.15))
    ax.axis("off")
    rows = [
        ("A. Private preference: Retrieve & Restore", 2.65,
         ["Open the lid", "Ask which item", "Retrieve the cup", "Replace the lid", "Finish"],
         DATA["example_traces"][0]),
        ("B. Observable fact: Reveal & Inspect", .55,
         ["Move the screen", "Inspect the label", "Report the code", "Finish"],
         DATA["example_traces"][1]),
    ]
    for title, y, labels, trace in rows:
        ax.text(.02, y+1.18, title, fontweight="bold", fontsize=8.7)
        for i, (label, turn) in enumerate(zip(labels, trace["turns"])):
            decision = turn["gate"]["decision"]
            p = turn["gate"]["p_ask"]
            ask = decision == "ASK"
            done = turn.get("action", {}).get("kind") == "DONE"
            face = "#FFF2D8" if ask else ("#F2F5F8" if done else "#ECF6F2")
            edge = "#CC9A45" if ask else ("#BAC5CF" if done else "#94BDB0")
            x = .02 + i*2.02
            box(ax, x, y, 1.79, .95, decision, f"{label}\np(ASK) = {p:.2f}",
                face=face, edge=edge, title_color=AMBER if ask else TEAL,
                title_size=7.4, body_size=7.2)
            if i+1 < len(labels):
                arrow(ax, [(x+1.83, y+.475), (x+1.97, y+.475)])
        if len(labels) == 4:
            ax.text(9.03, y+.48, "No question\nrequired", ha="center", va="center",
                    fontsize=8, color=TEAL, linespacing=1.4)
    ax.text(.03, 2.32, "Requested choice: blue cup or green block.  Answer: blue cup.",
            fontsize=7.5, color=MUTED)
    ax.text(.03, .12, "Both recorded episodes pass the task evaluator.  ASK threshold: 0.5.",
            fontsize=7.4, color=MUTED)
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    save(fig, "clarification_examples")


def efficiency_tradeoff():
    charts = DATA["ppt_values"]["method_charts"]
    success = np.array(charts[0]["percentages"])
    colors = [GRAY, BLUE, TEAL]
    markers = ["o", "s", "D"]
    labels = ["NoAsk", "LLM-Gate", "Jev-Gate"]
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.55), sharey=True)
    for j, ax in enumerate(axes):
        x = charts[j+1]["percentages"]
        ax.grid(color="#E1E7EC", lw=.65, zorder=0)
        for i in range(3):
            ax.scatter(x[i], success[i], s=56, marker=markers[i], color=colors[i],
                       edgecolor="white", linewidth=.7, zorder=3)
            xytext = [(7, 7), (-3, 8), (0, -15)][i]
            ax.annotate(labels[i], (x[i], success[i]), xytext=xytext,
                        textcoords="offset points", ha=["left", "right", "center"][i],
                        fontsize=8, color=colors[i], fontweight="bold")
        ax.set(xlim=(0, 110), ylim=(70, 105), yticks=[70, 80, 90, 100],
               xticks=[0, 25, 50, 75, 100])
        ax.set_xlabel(["Relative API time (%)", "Relative estimated cost (%)"][j])
        ax.set_title(["(a) Success and API time", "(b) Success and estimated cost"][j], loc="left")
    axes[0].set_ylabel("Task success (%)")
    fig.tight_layout(w_pad=1.3)
    save(fig, "efficiency_tradeoff")


def aggregate_comparison():
    charts = DATA["ppt_values"]["method_charts"]
    titles = ["(a) Task success", "(b) Relative API time", "(c) Relative estimated cost"]
    fig, axes = plt.subplots(1, 3, figsize=(6.6, 2.12))
    for ax, chart, title in zip(axes, charts, titles):
        bars = ax.bar(range(3), chart["percentages"], color=[GRAY, BLUE, TEAL], width=.6)
        ax.set_xticks(range(3), chart["categories"], rotation=15)
        ax.set_ylim(0, 116)
        ax.set_yticks([0, 50, 100], ["0%", "50%", "100%"])
        ax.set_title(title, fontsize=8.5, pad=9)
        ax.set_axisbelow(True)
        ax.yaxis.grid(True, color="#E1E7EC", linewidth=.6)
        for bar, value in zip(bars, chart["percentages"]):
            ax.text(bar.get_x()+bar.get_width()/2, value+2.5, f"{value:.1f}%",
                    ha="center", va="bottom", fontsize=7.6)
    fig.tight_layout(w_pad=.8, pad=.3)
    save(fig, "aggregate_comparison")


def task_heatmap():
    counts = np.array(DATA["success_counts"])
    assert list(counts.sum(axis=0)) == [21, 27, 26]
    cmap = LinearSegmentedColormap.from_list("task_success", ["#F9ECE7", "#DAEDE7", "#087F70"])
    fig, ax = plt.subplots(figsize=(6.6, 3.25))
    im = ax.imshow(counts, vmin=0, vmax=3, cmap=cmap, aspect="auto")
    ax.set_xticks([0, 1, 2], ["NoAsk\nTotal: 21/27", "LLM-Gate\nTotal: 27/27", "Jev-Gate\nTotal: 26/27"])
    ax.xaxis.tick_top()
    ax.tick_params(axis="both", which="both", length=0)
    ax.tick_params(axis="x", pad=8)
    ax.set_yticks(range(9), DATA["task_names"])
    ax.set_xticks(np.arange(-.5, 3, 1), minor=True)
    ax.set_yticks(np.arange(-.5, 9, 1), minor=True)
    ax.grid(which="minor", color="white", lw=2)
    for row in range(9):
        for col in range(3):
            v = counts[row, col]
            ax.text(col, row, f"{v}/3", ha="center", va="center", fontweight="bold",
                    color="white" if v==3 else INK, fontsize=8.3)
    for spine in ax.spines.values():
        spine.set_visible(False)
    cbar = fig.colorbar(im, ax=ax, ticks=[0, 1, 2, 3], fraction=.038, pad=.035)
    cbar.set_label("Successful cases (out of 3)", fontsize=8)
    cbar.outline.set_visible(False)
    fig.tight_layout(pad=.45)
    save(fig, "task_success_heatmap")


if __name__ == "__main__":
    task_gallery()
    benchmark_protocol()
    clarification_examples()
    efficiency_tradeoff()
    aggregate_comparison()
    task_heatmap()
    print("Built six figures as PDF, SVG, and PNG from verified local inputs.")
