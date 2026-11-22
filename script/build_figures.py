"""Plot measured benchmark tables."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tables', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    rows = json.loads(args.tables.read_text())['methods']
    import matplotlib.pyplot as plt
    groups = {
        'decision_methods': [('deepseek_noask', 'NoAsk'), ('deepseek_llm_gate', 'LLM-Gate'), ('deepseek_jev_gate', 'Jev-Gate')],
        'models': [('gpt_llm_gate', 'GPT-5.6'), ('deepseek_llm_gate', 'DeepSeek Flash'), ('glm_llm_gate', 'GLM 5.2')],
    }
    metrics = [('success_pct', 'Task success (%)'), ('api_time_s', 'API time (s)'),
               ('estimated_usd', 'Estimated API cost (USD)'), ('unnecessary_ask_pct', 'Unnecessary ASK (%)')]
    args.output.mkdir(parents=True, exist_ok=True)
    for name, items in groups.items():
        fig, axes = plt.subplots(1, 4, figsize=(13, 3.3), layout='constrained')
        for ax, (metric, title) in zip(axes, metrics):
            for i, (key, label) in enumerate(items):
                value = rows[key][metric]
                if value is None:
                    label_text = 'N/A' if metric=='unnecessary_ask_pct' and key=='deepseek_noask' else 'Unknown'
                    ax.text(i, .02, label_text, ha='center', transform=ax.get_xaxis_transform())
                else:
                    ax.bar(i, value, color=['#8d99ae', '#457b9d', '#2a9d8f'][i])
            ax.set_xticks(range(len(items)), [label for _, label in items], rotation=20, ha='right')
            ax.set_title(title)
            ax.set_ylim(bottom=0)
            if metric.endswith('_pct'):
                ax.set_ylim(0, 100)
            ax.spines[['top', 'right']].set_visible(False)
        for extension in ('png', 'pdf'):
            fig.savefig(args.output / (name + '.' + extension), dpi=200)
        plt.close(fig)


if __name__ == '__main__':
    main()
