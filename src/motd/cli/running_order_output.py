"""
CLI output formatting for running order analysis results.

This module handles all display logic for the analyze-running-order command,
keeping the CLI command itself focused on orchestration.
"""

import click
from pathlib import Path
from motd.pipeline.models import RunningOrderResult, MatchBoundary


def display_running_order_results(
    result: RunningOrderResult,
    ground_truth: dict[int, float] | None,
    fixtures: list[dict]
) -> tuple[list[float], list[float]]:
    """
    Display running order results with match boundaries and strategy comparison.

    Args:
        result: Complete running order with boundaries
        ground_truth: Optional ground truth timestamps {position: seconds}
        fixtures: Fixture list for context

    Returns:
        Tuple of (venue_diffs, clustering_diffs) for summary statistics
    """
    click.echo(f"{'='*60}")
    click.echo("RUNNING ORDER WITH BOUNDARIES")
    click.echo(f"{'='*60}\n")

    # Track strategy comparison stats
    venue_diffs = []
    clustering_diffs = []

    for i, match in enumerate(result.matches, 1):
        # Format timestamps as MM:SS
        match_start_str = f"{int(match.match_start // 60):02d}:{int(match.match_start % 60):02d}"
        highlights_start_str = f"{int(match.highlights_start // 60):02d}:{int(match.highlights_start % 60):02d}"
        highlights_end_str = f"{int(match.highlights_end // 60):02d}:{int(match.highlights_end % 60):02d}"
        match_end_str = f"{int(match.match_end // 60):02d}:{int(match.match_end % 60):02d}"

        # Calculate durations
        intro_duration = match.highlights_start - match.match_start
        highlights_duration = match.highlights_end - match.highlights_start
        postmatch_duration = match.match_end - match.highlights_end
        total_duration = match.match_end - match.match_start

        click.echo(f"Match {i}: {match.teams[0]} vs {match.teams[1]}")

        # Strategy comparison section
        if ground_truth and i in ground_truth:
            gt = ground_truth[i]
            gt_str = f"{int(gt // 60):02d}:{int(gt % 60):02d}"
            click.echo(f"  Ground Truth:        {gt_str}")

        click.echo(f"\n  Strategy Results:")

        # Venue strategy
        if match.venue_result:
            venue_ts = match.venue_result.get('timestamp')
            venue_str = f"{int(venue_ts // 60):02d}:{int(venue_ts % 60):02d}"
            if ground_truth and i in ground_truth:
                venue_diff = venue_ts - ground_truth[i]
                venue_diffs.append(abs(venue_diff))
                diff_str = f"({venue_diff:+.1f}s)" if venue_diff != 0 else "✓"
                click.echo(f"    Venue:             {venue_str} {diff_str}")
            else:
                click.echo(f"    Venue:             {venue_str}")
        else:
            click.echo(f"    Venue:             (not detected)")

        # Clustering strategy
        if match.clustering_result:
            cluster_ts = match.clustering_result.get('timestamp')

            if cluster_ts is not None:
                cluster_str = f"{int(cluster_ts // 60):02d}:{int(cluster_ts % 60):02d}"
                cluster_density = match.clustering_result.get('cluster_density', 0)
                cluster_size = match.clustering_result.get('cluster_size', 0)

                if ground_truth and i in ground_truth:
                    cluster_diff = cluster_ts - ground_truth[i]
                    clustering_diffs.append(abs(cluster_diff))
                    diff_str = f"({cluster_diff:+.1f}s)" if cluster_diff != 0 else "✓"
                    click.echo(f"    Clustering:        {cluster_str} {diff_str} (density: {cluster_density:.2f}, size: {cluster_size})")
                else:
                    click.echo(f"    Clustering:        {cluster_str} (density: {cluster_density:.2f}, size: {cluster_size})")
            else:
                # Clustering returned diagnostics but no result
                click.echo(f"    Clustering:        (not detected)")
        else:
            click.echo(f"    Clustering:        (not detected)")

        # Validation status (venue as primary, clustering as validator)
        _display_validation_status(match)

        click.echo(f"\n  Boundaries (using venue):")
        click.echo(f"    Intro:       {match_start_str} → {highlights_start_str} ({intro_duration:.0f}s)")
        click.echo(f"    Highlights:  {highlights_start_str} → {highlights_end_str} ({highlights_duration:.0f}s)")
        click.echo(f"    Post-match:  {highlights_end_str} → {match_end_str} ({postmatch_duration:.0f}s)")
        click.echo(f"    Total:       {match_start_str} → {match_end_str} ({total_duration:.0f}s)")
        click.echo()

    return venue_diffs, clustering_diffs


def _display_validation_status(match: MatchBoundary) -> None:
    """Display cross-validation status for a match."""
    if not match.validation:
        # Validation should always be present after boundary detection
        return

    val = match.validation

    if val.status == 'validated':
        # Perfect agreement - no warning
        click.echo(f"    Validation:        ✓ validated ({val.difference_seconds:.1f}s difference)")
    elif val.status == 'minor_discrepancy':
        # Minor discrepancy - yellow warning
        click.echo(click.style(f"    Validation:        ⚠ minor discrepancy ({val.difference_seconds:.1f}s)", fg='yellow'))
        click.echo(click.style(f"                       → Using venue result, flagged for review", fg='yellow', dim=True))
    elif val.status == 'major_discrepancy':
        # Major discrepancy - red warning
        click.echo(click.style(f"    Validation:        ✗ MAJOR DISCREPANCY ({val.difference_seconds:.1f}s)", fg='red', bold=True))
        click.echo(click.style(f"                       → Manual review REQUIRED", fg='red'))
    elif val.status == 'clustering_failed':
        # Clustering didn't detect - lower confidence but acceptable
        click.echo(f"    Validation:        ⓘ venue only (clustering failed, confidence {val.confidence})")


def display_validation_summary(
    result: RunningOrderResult,
    venue_diffs: list[float],
    clustering_diffs: list[float]
) -> None:
    """
    Display strategy comparison summary statistics.

    Args:
        result: Complete running order with boundaries
        venue_diffs: List of venue strategy differences from ground truth
        clustering_diffs: List of clustering strategy differences from ground truth
    """
    click.echo(f"{'='*60}")
    click.echo("STRATEGY COMPARISON SUMMARY")
    click.echo(f"{'='*60}\n")

    # Count matches with both strategies + agreement
    agreement_count = 0
    total_with_both = 0

    for match in result.matches:
        if match.validation:
            if match.validation.status in {'validated', 'minor_discrepancy', 'major_discrepancy'}:
                total_with_both += 1
                if match.validation.status == 'validated':
                    agreement_count += 1

    if total_with_both > 0:
        agreement_rate = agreement_count / total_with_both
        click.echo(f"Matches where both strategies detected: {total_with_both}/{len(result.matches)}")
        click.echo(f"Strategies agree (±10s):                {agreement_count}/{total_with_both} ({agreement_rate:.0%})")
        click.echo()

    if venue_diffs:
        avg_venue_diff = sum(venue_diffs) / len(venue_diffs)
        click.echo(f"Venue Strategy:")
        click.echo(f"  Average difference from ground truth:  {avg_venue_diff:.2f}s")
        click.echo(f"  Within ±5s:                            {sum(1 for d in venue_diffs if d <= 5)}/{len(venue_diffs)}")
        click.echo(f"  Within ±10s:                           {sum(1 for d in venue_diffs if d <= 10)}/{len(venue_diffs)}")
        click.echo()

    if clustering_diffs:
        avg_cluster_diff = sum(clustering_diffs) / len(clustering_diffs)
        click.echo(f"Clustering Strategy:")
        click.echo(f"  Average difference from ground truth:  {avg_cluster_diff:.2f}s")
        click.echo(f"  Within ±10s:                           {sum(1 for d in clustering_diffs if d <= 10)}/{len(clustering_diffs)}")
        click.echo(f"  Within ±30s:                           {sum(1 for d in clustering_diffs if d <= 30)}/{len(clustering_diffs)}")
        click.echo()
