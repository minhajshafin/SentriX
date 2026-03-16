#!/usr/bin/env python3
"""
Week 11: Paper Figure Generation
Generates all publication-quality figures for the SentriX paper.

Figures produced (saved to ml-pipeline/figures/):
  fig1_model_comparison.pdf/png        - Grouped CV model comparison
  fig2_generalization_heatmap.pdf/png  - Cross-protocol generalization gap
  fig3_per_class_f1.pdf/png            - Per-class precision/recall/F1 (best model)
  fig4_feature_drift.pdf/png           - Legacy vs behavioral feature drift
  fig5_anomaly_distribution.pdf/png    - Runtime anomaly score distribution by protocol
  fig6_threshold_sensitivity.pdf/png   - Detection threshold precision/recall/F1
  fig7_kl_divergence.pdf/png           - KL divergence heatmap by feature × class
"""

import json
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import seaborn as sns

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS = REPO_ROOT / 'ml-pipeline' / 'reports'
FIGURES = REPO_ROOT / 'ml-pipeline' / 'figures'
FEATURES_JSONL = Path('/tmp/sentrix-week8/features.jsonl')
WEEK10_ANALYSIS = Path('/tmp/sentrix-week8/week10_feature_analysis.json')

FIGURES.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Shared style
# ---------------------------------------------------------------------------
PALETTE = {
    'lightgbm':     '#2196F3',
    'random_forest':'#4CAF50',
    'mlp':          '#FF9800',
    'logreg':       '#9C27B0',
    'mqtt':         '#1565C0',
    'coap':         '#2E7D32',
    'full':         '#37474F',
    'normalized_plus_pid': '#78909C',
}

plt.rcParams.update({
    'figure.dpi': 150,
    'font.size': 10,
    'axes.titlesize': 12,
    'axes.labelsize': 10,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'figure.titlesize': 13,
})

MODEL_LABELS = {
    'lightgbm':     'LightGBM',
    'random_forest':'Random Forest',
    'mlp':          'MLP',
    'logreg':       'Logistic Reg.',
}

SPLIT_LABELS = {
    'grouped_cv':          'Grouped CV\n(in-protocol)',
    'cross_coap_to_mqtt':  'CoAP → MQTT\n(cross-protocol)',
    'cross_mqtt_to_coap':  'MQTT → CoAP\n(cross-protocol)',
}

FEATURE_SET_LABELS = {
    'full': 'Full (33-dim)',
    'normalized_plus_pid': 'Normalized + PID',
}

def save(fig, name):
    path = FIGURES / f'{name}.png'
    fig.savefig(path, bbox_inches='tight', dpi=150)
    print(f'  Saved: {path}')
    plt.close(fig)


# ---------------------------------------------------------------------------
# Fig 1: Model Comparison (Grouped CV)
# ---------------------------------------------------------------------------
def fig1_model_comparison():
    df = pd.read_csv(REPORTS / 'week5_baseline_metrics.csv')
    gdf = df[df['split'] == 'grouped_cv'].copy()

    models = ['lightgbm', 'random_forest', 'mlp', 'logreg']
    feature_sets = ['full', 'normalized_plus_pid']
    metrics = ['f1_macro', 'f1_weighted', 'accuracy']
    metric_labels = ['F1-Macro', 'F1-Weighted', 'Accuracy']

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), sharey=False)

    for ax, metric, mlabel in zip(axes, metrics, metric_labels):
        x = np.arange(len(models))
        width = 0.35
        for i, fs in enumerate(feature_sets):
            vals = []
            for m in models:
                row = gdf[(gdf['model'] == m) & (gdf['feature_set'] == fs)]
                vals.append(row[metric].values[0] if len(row) else 0.0)
            color = PALETTE[fs]
            bars = ax.bar(x + i * width - width / 2, vals, width,
                          label=FEATURE_SET_LABELS[fs], color=color, alpha=0.85,
                          edgecolor='white', linewidth=0.5)
            for bar, v in zip(bars, vals):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                        f'{v:.2f}', ha='center', va='bottom', fontsize=7.5)

        ax.set_xticks(x)
        ax.set_xticklabels([MODEL_LABELS[m] for m in models], rotation=20, ha='right')
        ax.set_ylabel(mlabel)
        ax.set_title(f'{mlabel} — Grouped CV')
        ax.set_ylim(0, 1.05)
        ax.axhline(0.5, color='gray', linestyle='--', linewidth=0.7, alpha=0.5)
        ax.grid(axis='y', alpha=0.3)
        if ax == axes[0]:
            ax.legend()

    fig.suptitle('SentriX Baseline Model Comparison (Grouped Cross-Validation)', fontweight='bold')
    fig.tight_layout()
    save(fig, 'fig1_model_comparison')


# ---------------------------------------------------------------------------
# Fig 2: Cross-Protocol Generalization Heatmap
# ---------------------------------------------------------------------------
def fig2_generalization_heatmap():
    df = pd.read_csv(REPORTS / 'week5_baseline_metrics.csv')
    df = df[df['feature_set'] == 'full']

    models = ['lightgbm', 'random_forest', 'mlp', 'logreg']
    splits = ['grouped_cv', 'cross_coap_to_mqtt', 'cross_mqtt_to_coap']

    for metric, mlabel, fname in [
        ('f1_macro',   'F1-Macro',   'fig2_generalization_heatmap_f1macro'),
        ('f1_weighted','F1-Weighted','fig2_generalization_heatmap_f1weighted'),
    ]:
        pivot = pd.DataFrame(index=[MODEL_LABELS[m] for m in models],
                             columns=[SPLIT_LABELS[s] for s in splits])
        for m in models:
            for s in splits:
                row = df[(df['model'] == m) & (df['split'] == s)]
                pivot.loc[MODEL_LABELS[m], SPLIT_LABELS[s]] = (
                    round(row[metric].values[0], 4) if len(row) else float('nan')
                )
        pivot = pivot.astype(float)

        fig, ax = plt.subplots(figsize=(8, 4))
        sns.heatmap(pivot, annot=True, fmt='.3f', cmap='RdYlGn',
                    vmin=0, vmax=1, ax=ax, linewidths=0.5,
                    cbar_kws={'label': mlabel})
        ax.set_title(f'Cross-Protocol Generalization — {mlabel} (feature set: full)',
                     fontweight='bold', pad=12)
        ax.set_xlabel('Evaluation Split')
        ax.set_ylabel('Model')

        # Annotate the generalization gap
        lgbm_gcv = pivot.loc[MODEL_LABELS['lightgbm'],
                              SPLIT_LABELS['grouped_cv']]
        lgbm_cross = min(
            float(pivot.loc[MODEL_LABELS['lightgbm'], SPLIT_LABELS['cross_coap_to_mqtt']]),
            float(pivot.loc[MODEL_LABELS['lightgbm'], SPLIT_LABELS['cross_mqtt_to_coap']])
        )
        ax.text(0.5, -0.18,
                f'LightGBM generalization gap: {lgbm_gcv:.3f} (in-protocol) → '
                f'{lgbm_cross:.3f} (cross-protocol) = Δ {lgbm_gcv - lgbm_cross:.3f}',
                transform=ax.transAxes, ha='center', fontsize=9,
                color='#B71C1C', style='italic')

        fig.tight_layout()
        save(fig, fname)


# ---------------------------------------------------------------------------
# Fig 3: Per-Class Performance (Best Model: LightGBM full, grouped_cv)
# ---------------------------------------------------------------------------
def fig3_per_class_f1():
    df = pd.read_csv(REPORTS / 'week5_baseline_per_class_metrics.csv')
    best = df[(df['model'] == 'lightgbm') &
              (df['feature_set'] == 'full') &
              (df['split'] == 'grouped_cv')]

    label_order = ['benign', 'mqtt_protocol_abuse', 'mqtt_wildcard_abuse',
                   'mqtt_publish_flood', 'coap_request_flood', 'coap_protocol_abuse']
    label_display = {
        'benign':              'Benign',
        'mqtt_protocol_abuse': 'MQTT\nProtocol Abuse',
        'mqtt_wildcard_abuse': 'MQTT\nWildcard Abuse',
        'mqtt_publish_flood':  'MQTT\nPublish Flood',
        'coap_request_flood':  'CoAP\nRequest Flood',
        'coap_protocol_abuse': 'CoAP\nProtocol Abuse',
    }

    fig, ax = plt.subplots(figsize=(11, 5))
    x = np.arange(len(label_order))
    width = 0.25
    colors = ['#1565C0', '#2E7D32', '#F57F17']

    for i, (col, clabel) in enumerate(
        [('precision', 'Precision'), ('recall', 'Recall'), ('f1', 'F1-Score')]
    ):
        vals = []
        for lbl in label_order:
            row = best[best['label'] == lbl]
            vals.append(row[col].values[0] if len(row) else 0.0)
        bars = ax.bar(x + (i - 1) * width, vals, width,
                      label=clabel, color=colors[i], alpha=0.85,
                      edgecolor='white', linewidth=0.5)
        for bar, v in zip(bars, vals):
            if v > 0.01:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                        f'{v:.2f}', ha='center', va='bottom', fontsize=7.5)

    ax.set_xticks(x)
    ax.set_xticklabels([label_display[l] for l in label_order])
    ax.set_ylabel('Score')
    ax.set_ylim(0, 1.15)
    ax.set_title('Per-Class Precision / Recall / F1  —  LightGBM (full features, grouped CV)',
                 fontweight='bold')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    # Colour-code x-tick labels by protocol
    for tick, lbl in zip(ax.get_xticklabels(), label_order):
        if 'mqtt' in lbl:
            tick.set_color(PALETTE['mqtt'])
        elif 'coap' in lbl:
            tick.set_color(PALETTE['coap'])

    legend_patches = [
        mpatches.Patch(color=PALETTE['mqtt'], label='MQTT class'),
        mpatches.Patch(color=PALETTE['coap'], label='CoAP class'),
    ]
    ax.legend(handles=[
        mpatches.Patch(color='#1565C0', label='Precision'),
        mpatches.Patch(color='#2E7D32', label='Recall'),
        mpatches.Patch(color='#F57F17', label='F1-Score'),
    ] + legend_patches, loc='upper right', ncol=2)

    fig.tight_layout()
    save(fig, 'fig3_per_class_f1')


# ---------------------------------------------------------------------------
# Fig 4: Feature Drift (Legacy vs Behavioral)
# ---------------------------------------------------------------------------
def fig4_feature_drift():
    with open(WEEK10_ANALYSIS) as f:
        analysis = json.load(f)

    drift = analysis['per_feature_drift']
    features = list(drift.keys())
    avg_deltas = [drift[f]['avg_delta'] for f in features]
    avg_legacy = [drift[f]['avg_legacy'] for f in features]
    avg_behavioral = [drift[f]['avg_behavioral'] for f in features]

    # Sort by avg_delta descending
    order = sorted(range(len(features)), key=lambda i: avg_deltas[i], reverse=True)
    features_s = [features[i] for i in order]
    deltas_s = [avg_deltas[i] for i in order]
    legacy_s = [avg_legacy[i] for i in order]
    behavioral_s = [avg_behavioral[i] for i in order]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Left: feature drift bar chart
    y = range(len(features_s))
    bars = ax1.barh(list(y), deltas_s, color='#EF5350', alpha=0.8, edgecolor='white')
    ax1.set_yticks(list(y))
    ax1.set_yticklabels(features_s, fontsize=8)
    ax1.set_xlabel('Average |Legacy − Behavioral| Delta')
    ax1.set_title('Feature Drift: Legacy vs Behavioral\n(sorted by drift magnitude)', fontweight='bold')
    ax1.axvline(0.3, color='orange', linestyle='--', linewidth=1, label='Δ=0.30 threshold')
    ax1.axvline(0.5, color='red', linestyle='--', linewidth=1, label='Δ=0.50 threshold')
    ax1.legend(fontsize=8)
    ax1.grid(axis='x', alpha=0.3)

    # Right: legacy vs. behavioral scatter
    colors_scatter = ['#EF5350' if d > 0.4 else '#FFA726' if d > 0.2 else '#66BB6A'
                      for d in deltas_s]
    ax2.scatter(legacy_s, behavioral_s, c=colors_scatter, s=60, alpha=0.85,
                edgecolors='white', linewidth=0.5)
    lim_min = min(min(legacy_s), min(behavioral_s)) - 0.05
    lim_max = max(max(legacy_s), max(behavioral_s)) + 0.05
    ax2.plot([lim_min, lim_max], [lim_min, lim_max], 'k--', linewidth=1, alpha=0.5,
             label='Perfect alignment')
    for xi, yi, fi in zip(legacy_s, behavioral_s, features_s):
        if abs(xi - yi) > 0.35:
            ax2.annotate(fi, (xi, yi), textcoords='offset points',
                         xytext=(5, 3), fontsize=7)
    ax2.set_xlabel('Legacy Feature Mean Value')
    ax2.set_ylabel('Behavioral Feature Mean Value')
    ax2.set_title('Legacy vs Behavioral Feature Values\n(points off diagonal = high drift)',
                  fontweight='bold')

    legend_patches = [
        mpatches.Patch(color='#EF5350', label='High drift (Δ>0.4)'),
        mpatches.Patch(color='#FFA726', label='Moderate drift (0.2<Δ≤0.4)'),
        mpatches.Patch(color='#66BB6A', label='Low drift (Δ≤0.2)'),
    ]
    ax2.legend(handles=legend_patches, fontsize=8)
    ax2.grid(alpha=0.3)

    fig.suptitle('Protocol-Normalized Feature Drift Analysis (n=101 vectors)', fontweight='bold')
    fig.tight_layout()
    save(fig, 'fig4_feature_drift')


# ---------------------------------------------------------------------------
# Fig 5: Runtime Anomaly Score Distribution by Protocol
# ---------------------------------------------------------------------------
def fig5_anomaly_distribution():
    mqtt_scores, coap_scores = [], []
    with open(FEATURES_JSONL) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
                score = ev.get('decision', {}).get('anomaly_score')
                if score is None:
                    continue
                if ev.get('protocol') == 'mqtt':
                    mqtt_scores.append(score)
                elif ev.get('protocol') == 'coap':
                    coap_scores.append(score)
            except Exception:
                pass

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Left: KDE + histogram overlay
    ax = axes[0]
    bins = np.linspace(0, 1, 30)
    ax.hist(mqtt_scores, bins=bins, alpha=0.45, color=PALETTE['mqtt'],
            label=f'MQTT (n={len(mqtt_scores)})', density=True)
    ax.hist(coap_scores, bins=bins, alpha=0.45, color=PALETTE['coap'],
            label=f'CoAP (n={len(coap_scores)})', density=True)

    # KDE
    from scipy.stats import gaussian_kde
    if len(mqtt_scores) > 3:
        kde_x = np.linspace(0, 1, 300)
        kde_mqtt = gaussian_kde(mqtt_scores, bw_method=0.3)
        ax.plot(kde_x, kde_mqtt(kde_x), color=PALETTE['mqtt'], linewidth=2)
    if len(coap_scores) > 3:
        kde_x = np.linspace(0, 1, 300)
        kde_coap = gaussian_kde(coap_scores, bw_method=0.3)
        ax.plot(kde_x, kde_coap(kde_x), color=PALETTE['coap'], linewidth=2)

    ax.axvline(0.75, color='red', linestyle='--', linewidth=1.5, label='Alert threshold (0.75)')
    ax.axvline(0.30, color='orange', linestyle='--', linewidth=1.2, label='Elevated threshold (0.30)')
    ax.set_xlabel('Anomaly Score')
    ax.set_ylabel('Density')
    ax.set_title('Runtime Anomaly Score Distribution\nby Protocol (KDE + Histogram)', fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)

    # Right: Box plots + statistical summary
    ax2 = axes[1]
    data = [mqtt_scores, coap_scores]
    labels = [f'MQTT\n(n={len(mqtt_scores)})', f'CoAP\n(n={len(coap_scores)})']
    bp = ax2.boxplot(data, labels=labels, patch_artist=True,
                     medianprops=dict(color='white', linewidth=2))
    bp['boxes'][0].set_facecolor(PALETTE['mqtt'])
    bp['boxes'][0].set_alpha(0.7)
    if len(bp['boxes']) > 1:
        bp['boxes'][1].set_facecolor(PALETTE['coap'])
        bp['boxes'][1].set_alpha(0.7)

    # Overlay individual points
    for i, (scores, color) in enumerate([(mqtt_scores, PALETTE['mqtt']),
                                          (coap_scores, PALETTE['coap'])]):
        jitter = np.random.default_rng(42).uniform(-0.1, 0.1, len(scores))
        ax2.scatter(np.full(len(scores), i + 1) + jitter, scores,
                    color=color, alpha=0.3, s=12, zorder=3)

    ax2.axhline(0.75, color='red', linestyle='--', linewidth=1.5, label='Alert threshold')
    ax2.axhline(0.30, color='orange', linestyle='--', linewidth=1.2, label='Elevated threshold')
    ax2.set_ylabel('Anomaly Score')
    ax2.set_title('Protocol Anomaly Score\nBox Plot', fontweight='bold')
    ax2.legend()
    ax2.grid(axis='y', alpha=0.3)

    # Add stats text
    for i, (scores, label) in enumerate([(mqtt_scores, 'MQTT'), (coap_scores, 'CoAP')]):
        if scores:
            ax2.text(i + 1, max(scores) + 0.02,
                     f'μ={np.mean(scores):.3f}\np95={np.percentile(scores, 95):.3f}',
                     ha='center', fontsize=7.5, color='gray')

    fig.suptitle('SentriX Runtime Anomaly Scores — Live Proxy Inference (n=101)', fontweight='bold')
    fig.tight_layout()
    save(fig, 'fig5_anomaly_distribution')


# ---------------------------------------------------------------------------
# Fig 6: Detection Threshold Sensitivity
# ---------------------------------------------------------------------------
def fig6_threshold_sensitivity():
    scores = []
    with open(FEATURES_JSONL) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
                score = ev.get('decision', {}).get('anomaly_score')
                if score is not None:
                    scores.append(score)
            except Exception:
                pass

    scores = np.array(scores)
    # All current vectors are benign (no detections confirmed in week 10)
    # Ground truth: score >= 0.75 means attack (based on current data, all FP-free)
    # Simulate sensitivity by varying threshold and computing rates

    thresholds = np.linspace(0.10, 0.95, 200)
    detection_rate = []  # fraction flagged as anomalous
    false_alarm_est = []  # estimate: among those in benign range (<0.30), fraction flagged

    for t in thresholds:
        flagged = np.mean(scores >= t)
        detection_rate.append(flagged)
        # Among scores in benign zone, fraction falsely flagged at this threshold
        benign_zone = scores[scores < 0.40]
        fa = np.mean(benign_zone >= t) if len(benign_zone) else 0.0
        false_alarm_est.append(fa)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(thresholds, detection_rate, color='#1565C0', linewidth=2,
            label='Detection Rate (fraction flagged)')
    ax.plot(thresholds, false_alarm_est, color='#C62828', linewidth=2,
            linestyle='--', label='False Alarm Rate (est. from benign zone)')

    ax.axvline(0.75, color='red', linestyle=':', linewidth=1.5,
               label='Current threshold (0.75)')
    ax.axvline(0.30, color='orange', linestyle=':', linewidth=1.2,
               label='Elevated threshold (0.30)')

    # Mark operating point
    op_detected = float(np.mean(scores >= 0.75))
    op_fa = float(np.mean(scores[(scores < 0.40)] >= 0.75))
    ax.scatter([0.75], [op_detected], color='red', s=60, zorder=5)
    ax.scatter([0.75], [op_fa], color='darkred', s=60, zorder=5)
    ax.text(0.76, op_detected + 0.015, f'{op_detected:.1%} detected', fontsize=8, color='red')
    ax.text(0.76, op_fa + 0.005, f'{op_fa:.1%} false alarms', fontsize=8, color='darkred')

    ax.set_xlabel('Anomaly Score Threshold')
    ax.set_ylabel('Rate')
    ax.set_title('Detection Threshold Sensitivity Analysis\n(n=101 live proxy vectors)',
                 fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)
    ax.set_xlim(0.10, 0.95)
    ax.set_ylim(-0.02, 1.05)

    fig.tight_layout()
    save(fig, 'fig6_threshold_sensitivity')


# ---------------------------------------------------------------------------
# Fig 7: KL Divergence Heatmap (feature × attack_class)
# ---------------------------------------------------------------------------
def fig7_kl_divergence():
    df = pd.read_csv(REPORTS / 'kl_alignment_by_class.csv')

    # Pivot: features as rows, classes as columns, value=kl_symmetric
    pivot = df.pivot_table(index='feature', columns='attack_class',
                           values='kl_symmetric', aggfunc='mean')

    # Sort features by mean KL across classes
    pivot['_mean'] = pivot.mean(axis=1)
    pivot = pivot.sort_values('_mean', ascending=False).drop(columns='_mean')

    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(pivot, annot=True, fmt='.2f', cmap='YlOrRd',
                ax=ax, linewidths=0.3,
                cbar_kws={'label': 'Symmetric KL Divergence (↑ = less aligned)'})
    ax.set_title('Feature KL Divergence: MQTT vs CoAP by Attack Class\n'
                 '(lower = better cross-protocol feature alignment)',
                 fontweight='bold', pad=12)
    ax.set_xlabel('Attack Class')
    ax.set_ylabel('Feature')
    plt.xticks(rotation=20, ha='right')

    fig.tight_layout()
    save(fig, 'fig7_kl_divergence')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print('=== Week 11: Generating Paper Figures ===')
    print(f'Output dir: {FIGURES}')
    print()

    steps = [
        ('Fig 1 — Model Comparison (Grouped CV)',     fig1_model_comparison),
        ('Fig 2 — Generalization Heatmap',            fig2_generalization_heatmap),
        ('Fig 3 — Per-Class F1 (Best Model)',         fig3_per_class_f1),
        ('Fig 4 — Feature Drift Analysis',            fig4_feature_drift),
        ('Fig 5 — Anomaly Score Distribution',        fig5_anomaly_distribution),
        ('Fig 6 — Threshold Sensitivity',             fig6_threshold_sensitivity),
        ('Fig 7 — KL Divergence Heatmap',             fig7_kl_divergence),
    ]

    ok, failed = 0, []
    for label, fn in steps:
        print(f'  {label}...')
        try:
            fn()
            ok += 1
        except Exception as e:
            print(f'    ERROR: {e}')
            import traceback; traceback.print_exc()
            failed.append(label)

    print()
    print(f'Done: {ok}/{len(steps)} figures generated  |  Failed: {len(failed)}')
    if failed:
        for f in failed:
            print(f'  ✗ {f}')
    else:
        print('All figures saved successfully.')

    print()
    print('Generated files:')
    for p in sorted(FIGURES.iterdir()):
        print(f'  {p.name}')


if __name__ == '__main__':
    main()
