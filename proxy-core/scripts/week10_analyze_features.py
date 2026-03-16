#!/usr/bin/env python3

"""
Week 10: Statistical Analysis of Week 9 Feature Data
Analyze feature vectors and anomaly scores for detection performance validation
"""

import json
import statistics
from collections import defaultdict
from datetime import datetime

def analyze_features():
    """Analyze accumulated feature vectors from Week 9"""
    
    features_file = '/tmp/sentrix-week8/features.jsonl'
    
    # Load all features
    features = []
    protocol_stats = defaultdict(list)
    anomaly_scores = defaultdict(list)
    feature_matrix = defaultdict(list)
    
    try:
        with open(features_file, 'r') as f:
            for line in f:
                try:
                    feature = json.loads(line.strip())
                    features.append(feature)
                    
                    # Track by protocol
                    protocol = feature.get('protocol', 'unknown')
                    anomaly_score = feature.get('decision', {}).get('anomaly_score', 0)
                    
                    anomaly_scores[protocol].append(anomaly_score)
                    anomaly_scores['all'].append(anomaly_score)
                    
                    # Track feature vectors
                    legacy = feature.get('legacy', [])
                    behavioral = feature.get('behavioral', [])
                    
                    feature_matrix[protocol].append({
                        'legacy': legacy,
                        'behavioral': behavioral,
                        'active': feature.get('active', legacy),
                        'anomaly_score': anomaly_score
                    })
                except:
                    pass
    except FileNotFoundError:
        print(f"Feature file not found: {features_file}")
        return None
    
    if not features:
        print("No features loaded")
        return None
    
    # Compute statistics
    results = {
        'timestamp': datetime.now().isoformat(),
        'test': 'week10_feature_analysis',
        'summary': {
            'total_vectors': len(features),
            'by_protocol': {}
        },
        'anomaly_distribution': {},
        'per_feature_drift': {},
        'per_protocol_analysis': {}
    }
    
    # Protocol summary
    for protocol, scores in anomaly_scores.items():
        if protocol != 'all' and scores:
            results['summary']['by_protocol'][protocol] = len(scores)
    
    # Anomaly score distribution by protocol
    for protocol, scores in anomaly_scores.items():
        if scores:
            results['anomaly_distribution'][protocol] = {
                'count': len(scores),
                'min': min(scores),
                'max': max(scores),
                'mean': statistics.mean(scores),
                'median': statistics.median(scores),
                'stdev': statistics.stdev(scores) if len(scores) > 1 else 0,
                'p25': sorted(scores)[len(scores)//4],
                'p75': sorted(scores)[3*len(scores)//4],
                'p95': sorted(scores)[int(0.95*len(scores)-1)] if len(scores) > 1 else max(scores)
            }
    
    # Per-feature drift analysis (legacy vs behavioral)
    if features and 'legacy' in features[0] and 'behavioral' in features[0]:
        num_features = len(features[0]['legacy'])
        
        for feat_idx in range(num_features):
            legacy_vals = [f['legacy'][feat_idx] for f in features if len(f.get('legacy', [])) > feat_idx]
            behavioral_vals = [f['behavioral'][feat_idx] for f in features if len(f.get('behavioral', [])) > feat_idx]
            
            if legacy_vals and behavioral_vals:
                # Compute drift
                diffs = [abs(l - b) for l, b in zip(legacy_vals, behavioral_vals)]
                results['per_feature_drift'][f'f{feat_idx:02d}'] = {
                    'avg_delta': statistics.mean(diffs),
                    'max_delta': max(diffs),
                    'avg_legacy': statistics.mean(legacy_vals),
                    'avg_behavioral': statistics.mean(behavioral_vals)
                }
    
    # Per-protocol analysis
    for protocol, vectors in feature_matrix.items():
        if vectors:
            scores = [v['anomaly_score'] for v in vectors]
            results['per_protocol_analysis'][protocol] = {
                'count': len(vectors),
                'benign_ratio': sum(1 for s in scores if s < 0.3) / len(scores),
                'elevated_ratio': sum(1 for s in scores if 0.3 <= s < 0.75) / len(scores),
                'suspicious_ratio': sum(1 for s in scores if s >= 0.75) / len(scores),
                'anomaly_mean': statistics.mean(scores),
                'anomaly_stdev': statistics.stdev(scores) if len(scores) > 1 else 0
            }
    
    return results

def main():
    print("\n📊 Week 10: Feature Analysis\n")
    
    results = analyze_features()
    
    if not results:
        return
    
    # Display summary
    print(f"Total Feature Vectors: {results['summary']['total_vectors']}")
    print(f"By Protocol:")
    for protocol, count in results['summary']['by_protocol'].items():
        print(f"  • {protocol.upper()}: {count}")
    
    # Display anomaly distribution
    print(f"\n🎯 Anomaly Score Distribution:")
    for protocol, stats in results['anomaly_distribution'].items():
        print(f"\n  {protocol.upper()}:")
        print(f"    Min:    {stats['min']:.4f}")
        print(f"    P25:    {stats['p25']:.4f}")
        print(f"    Mean:   {stats['mean']:.4f}")
        print(f"    Median: {stats['median']:.4f}")
        print(f"    P75:    {stats['p75']:.4f}")
        print(f"    P95:    {stats['p95']:.4f}")
        print(f"    Max:    {stats['max']:.4f}")
        print(f"    StDev:  {stats['stdev']:.4f}")
    
    # Display per-protocol categorization
    print(f"\n🔍 Detection Classification by Protocol:")
    for protocol, analysis in results['per_protocol_analysis'].items():
        print(f"\n  {protocol.upper()}:")
        print(f"    Benign (<0.30):       {analysis['benign_ratio']*100:.1f}%")
        print(f"    Elevated (0.30-0.75): {analysis['elevated_ratio']*100:.1f}%")
        print(f"    Suspicious (≥0.75):   {analysis['suspicious_ratio']*100:.1f}%")
        print(f"    Mean Anomaly Score:   {analysis['anomaly_mean']:.4f}")
    
    # Show top drifting features
    print(f"\n📈 Feature Drift (Top 5):")
    sorted_drift = sorted(results['per_feature_drift'].items(), 
                         key=lambda x: x[1]['avg_delta'], reverse=True)[:5]
    for feat_name, drift in sorted_drift:
        print(f"  {feat_name}: Δ={drift['avg_delta']:.4f} " + 
              f"(legacy={drift['avg_legacy']:.3f}, behavioral={drift['avg_behavioral']:.3f})")
    
    # Save report
    report_path = '/tmp/sentrix-week8/week10_feature_analysis.json'
    with open(report_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Full analysis saved: {report_path}\n")
    
    return results

if __name__ == '__main__':
    main()
