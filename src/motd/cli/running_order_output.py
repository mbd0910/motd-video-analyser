"""
CLI output formatting for running order analysis results.

This module handles all display logic for the analyze-running-order command,
keeping the CLI command itself focused on orchestration.
"""

import click
from pathlib import Path
from motd.pipeline.models import RunningOrderResult, MatchBoundary


def _get_boundary_strategy_label(match: MatchBoundary) -> str:
    """
    Determine which strategy's timestamps are being used for boundaries.

    Returns dynamic label based on actual detection results:
    - Venue detected (validated) → "using venue, validated by clustering"
    - Venue detected (not validated) → "using venue"
    - Clustering only → "using clustering - venue failed"
    - Team mention only → "using team mention - venue & clustering failed"
    - None detected → "strategy unknown" (shouldn't happen)

    Args:
        match: MatchBoundary with strategy results

    Returns:
        Human-readable label for boundaries section
    """
    if match.venue_result and match.venue_result.get('timestamp') is not None:
        # Venue detected - check if validated
        if match.validation and match.validation.status == 'validated':
            return "Boundaries (using venue, validated by clustering)"
        else:
            return "Boundaries (using venue)"
    elif match.clustering_result and match.clustering_result.get('timestamp') is not None:
        return "Boundaries (using clustering - venue failed)"
    elif match.team_mention_result and match.team_mention_result.get('timestamp') is not None:
        return "Boundaries (using team mention - venue & clustering failed)"
    else:
        return "Boundaries (strategy unknown - check detection logic)"


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

        # Display boundaries with dynamic strategy label
        strategy_label = _get_boundary_strategy_label(match)
        click.echo(f"\n  {strategy_label}:")
        click.echo(f"    Intro:       {match_start_str} → {highlights_start_str} ({intro_duration:.0f}s)")
        click.echo(f"    Highlights:  {highlights_start_str} → {highlights_end_str} ({highlights_duration:.0f}s)")
        click.echo(f"    Post-match:  {highlights_end_str} → {match_end_str} ({postmatch_duration:.0f}s)")
        click.echo(f"    Total:       {match_start_str} → {match_end_str} ({total_duration:.0f}s)")

        # Display detection events for debugging (Task 012-03)
        _display_detection_events(match, i, result.matches)

        # Display gap analysis (Phase 1: Task 012-02)
        _display_gap_analysis(match, i, result.matches)

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


def _display_detection_events(match: MatchBoundary, match_number: int, all_matches: list[MatchBoundary]) -> None:
    """
    Display intermediate detection events that led to boundary determination.

    Helps debugging by showing:
    - Where FT graphics were found (marks highlights_end)
    - Where first scoreboards appeared (marks highlights_start usually)
    - Future: Where interludes/table reviews detected (needs model extension)

    Only displays section if at least one event exists.

    Args:
        match: Current match boundary
        match_number: Match position (1-7)
        all_matches: All matches in running order (for context)
    """
    events = []

    # FT Graphic detection (primary signal for highlights_end)
    if match.ft_graphic_time:
        ft_str = f"{int(match.ft_graphic_time // 60):02d}:{int(match.ft_graphic_time % 60):02d}"
        events.append(f"    FT Graphic:      {ft_str} ({match.ft_graphic_time:.1f}s)")

    # First scoreboard detection (backup signal for highlights_start)
    if match.first_scoreboard_time:
        sb_str = f"{int(match.first_scoreboard_time // 60):02d}:{int(match.first_scoreboard_time % 60):02d}"
        events.append(f"    First Scoreboard: {sb_str} ({match.first_scoreboard_time:.1f}s)")

    # TODO: Interlude/table detection (need to extend MatchBoundary model first)
    # Currently only logged by RunningOrderDetector, not stored for display
    # if match.interlude_detected:
    #     interlude_str = f"{int(match.interlude_detected['timestamp'] // 60):02d}:..."
    #     keyword = match.interlude_detected.get('keyword', 'unknown')
    #     events.append(f"    Interlude:       {interlude_str} (keyword: '{keyword}')")

    # Only show section if we have events
    if events:
        click.echo(f"\n  Detection Events:")
        for event in events:
            click.echo(event)


def _display_gap_analysis(match: MatchBoundary, match_number: int, all_matches: list[MatchBoundary]) -> None:
    """
    Display gap analysis between current match's highlights_end and next match's match_start.

    Part of Task 012-02: Helps identify where interludes/long analysis periods occur.

    Args:
        match: Current match boundary
        match_number: Match position (1-7)
        all_matches: All matches in running order
    """
    # For all matches except the last, show the gap to next match
    if match_number < len(all_matches):
        next_match = all_matches[match_number]  # match_number is 1-indexed
        gap_seconds = next_match.match_start - match.highlights_end
        gap_mm = int(gap_seconds // 60)
        gap_ss = int(gap_seconds % 60)

        # Flag if gap is suspiciously long (>120s = 2 minutes)
        # Typical post-match analysis: 30-90s
        # Long gap suggests interlude or extended analysis
        if gap_seconds > 120:
            flag = click.style(" ⚠️ LONG GAP (potential interlude)", fg='yellow', bold=True)
        else:
            flag = ""

        click.echo(f"\n  Gap Analysis:")
        click.echo(f"    highlights_end → next match_start: {gap_mm:02d}:{gap_ss:02d} ({gap_seconds:.0f}s){flag}")

        if gap_seconds > 120:
            click.echo(click.style(f"    → Gap includes post-match analysis + potential interlude/review", fg='yellow', dim=True))


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
