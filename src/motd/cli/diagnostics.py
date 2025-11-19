"""
Debug diagnostics generation for clustering strategy analysis.

Generates comprehensive JSON diagnostics for algorithm tuning and debugging.
"""

import json
import click
from pathlib import Path
from motd.pipeline.models import RunningOrderResult
from motd.analysis.running_order_detector import RunningOrderDetector


def generate_clustering_diagnostics(
    result: RunningOrderResult,
    ground_truth: dict[int, float],
    detector: RunningOrderDetector,
    episode_id: str,
    output_dir: Path
) -> Path:
    """
    Generate comprehensive clustering diagnostics JSON for debugging.

    Args:
        result: Complete running order with boundaries
        ground_truth: Ground truth timestamps {position: seconds}
        detector: Detector instance (for parameters)
        episode_id: Episode identifier
        output_dir: Base output directory

    Returns:
        Path to generated diagnostics JSON file
    """
    click.echo(f"{'='*60}")
    click.echo("GENERATING DEBUG DIAGNOSTICS")
    click.echo(f"{'='*60}\n")

    diagnostics = {
        "episode_id": episode_id,
        "parameters": {
            "clustering_window_seconds": detector.CLUSTERING_WINDOW_SECONDS,
            "clustering_min_density": detector.CLUSTERING_MIN_DENSITY,
            "clustering_min_size": detector.CLUSTERING_MIN_SIZE
        },
        "ground_truth": ground_truth,
        "matches": []
    }

    for i, match in enumerate(result.matches, 1):
        # Build match diagnostic entry
        match_diag = {
            "match_number": i,
            "teams": list(match.teams),
            "ground_truth": ground_truth.get(i),
            "venue_result": match.venue_result,
            "clustering_result": match.clustering_result,
            "insights": {}
        }

        # Generate insights
        gt = ground_truth.get(i)
        insights = match_diag["insights"]

        # Determine detection status
        if match.clustering_result:
            if 'diagnostics' in match.clustering_result:
                # Has diagnostics - check if successful
                diag = match.clustering_result['diagnostics']
                if 'failure_reason' in diag:
                    insights['detection_status'] = 'failed'
                    insights['failure_reason'] = diag.get('failure_reason')
                    insights['failure_details'] = diag.get('failure_details')
                elif gt and match.clustering_result.get('timestamp'):
                    cluster_ts = match.clustering_result['timestamp']
                    diff = abs(cluster_ts - gt)
                    if diff <= 10:
                        insights['detection_status'] = 'success'
                    elif diff <= 30:
                        insights['detection_status'] = 'acceptable'
                    else:
                        insights['detection_status'] = 'outlier'
                else:
                    insights['detection_status'] = 'success'
            else:
                insights['detection_status'] = 'success_no_diagnostics'
        else:
            insights['detection_status'] = 'failed'

        # Agreement with venue
        if match.venue_result and match.clustering_result:
            if 'timestamp' in match.clustering_result and 'timestamp' in match.venue_result:
                venue_ts = match.venue_result['timestamp']
                cluster_ts = match.clustering_result['timestamp']
                diff = abs(venue_ts - cluster_ts)

                if diff == 0:
                    insights['agreement_with_venue'] = 'perfect'
                elif diff <= 5:
                    insights['agreement_with_venue'] = 'excellent'
                elif diff <= 10:
                    insights['agreement_with_venue'] = 'good'
                elif diff <= 30:
                    insights['agreement_with_venue'] = 'acceptable'
                else:
                    insights['agreement_with_venue'] = 'disagreement'

                insights['venue_clustering_diff'] = round(diff, 2)

        # Recommendations
        recommendations = _generate_recommendations(
            insights,
            match,
            gt,
            detector
        )
        insights['recommendations'] = recommendations

        diagnostics["matches"].append(match_diag)

    # Save debug JSON
    debug_output = output_dir / f'{episode_id}/clustering_debug.json'
    debug_output.parent.mkdir(parents=True, exist_ok=True)
    debug_output.write_text(json.dumps(diagnostics, indent=2))

    click.echo(f"✓ Debug diagnostics saved to: {debug_output}")
    click.echo()

    return debug_output


def _generate_recommendations(
    insights: dict,
    match,
    ground_truth: float | None,
    detector: RunningOrderDetector
) -> list[str]:
    """Generate tuning recommendations based on detection results."""
    recommendations = []

    if insights.get('detection_status') == 'failed':
        if match.clustering_result and 'diagnostics' in match.clustering_result:
            diag = match.clustering_result['diagnostics']
            failure = diag.get('failure_reason')

            if failure == 'no_valid_cluster':
                recommendations.append("No valid clusters found - consider:")
                recommendations.append(f"  - Lowering min_density (currently {detector.CLUSTERING_MIN_DENSITY})")
                recommendations.append(f"  - Lowering min_size (currently {detector.CLUSTERING_MIN_SIZE})")
                recommendations.append(f"  - Increasing window_seconds (currently {detector.CLUSTERING_WINDOW_SECONDS}s)")
            elif failure == 'no_windows':
                recommendations.append("No co-mention windows found - consider:")
                recommendations.append(f"  - Increasing window_seconds (currently {detector.CLUSTERING_WINDOW_SECONDS}s)")
            elif failure == 'no_mentions':
                recommendations.append("Teams not mentioned in transcript - manual inspection needed")

    elif insights.get('detection_status') == 'outlier':
        if match.clustering_result and 'diagnostics' in match.clustering_result:
            diag = match.clustering_result['diagnostics']
            if 'alternative_clusters' in diag and len(diag['alternative_clusters']) > 0:
                # Check if any alternative is closer to ground truth
                for alt in diag['alternative_clusters']:
                    if ground_truth:
                        alt_diff = abs(alt['start'] - ground_truth)
                        current_diff = abs(match.clustering_result['timestamp'] - ground_truth)
                        if alt_diff < current_diff:
                            recommendations.append(f"Alternative cluster at {alt['start']:.1f}s is {current_diff - alt_diff:.1f}s closer to ground truth")
                            recommendations.append("Consider preferring earliness over density in cluster selection")
                            break

    if insights.get('agreement_with_venue') == 'perfect':
        recommendations.append("Perfect match with venue strategy - algorithm working correctly")

    return recommendations
