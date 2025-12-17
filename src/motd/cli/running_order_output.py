"""
CLI output formatting for running order analysis results.

This module handles all display logic for the analyze-running-order command,
keeping the CLI command itself focused on orchestration.
"""

import click
from pathlib import Path
from motd.pipeline.models import RunningOrderResult, MatchBoundary


def _fmt_timestamp(ts: float | None) -> str:
    """Format timestamp as MM:SS, or '--:--' if None."""
    if ts is None:
        return "--:--"
    return f"{int(ts // 60):02d}:{int(ts % 60):02d}"


def _fmt_duration(dur: float | None) -> str:
    """Format duration in seconds, or 'N/A' if None."""
    return f"{dur:.0f}s" if dur is not None else "N/A"


def _get_home_away_teams(teams: tuple[str, str], fixtures: list[dict]) -> tuple[str, str]:
    """
    Reorder teams from alphabetical to home/away based on fixtures.

    Args:
        teams: Alphabetically sorted team pair (e.g., ("Arsenal", "Burnley"))
        fixtures: List of fixture dicts with home_team, away_team

    Returns:
        Tuple of (home_team, away_team), or original order if not found
    """
    team_set = set(teams)

    for fixture in fixtures:
        fixture_teams = {fixture['home_team'], fixture['away_team']}
        if team_set == fixture_teams:
            return (fixture['home_team'], fixture['away_team'])

    # Fallback: return original alphabetical order if fixture not found
    return teams


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
    fixtures: list[dict]
) -> None:
    """
    Display running order results with match boundaries and strategy comparison.

    Args:
        result: Complete running order with boundaries
        fixtures: Fixture list for context
    """
    click.echo(f"{'='*60}")
    click.echo("RUNNING ORDER WITH BOUNDARIES")
    click.echo(f"{'='*60}\n")

    for i, match in enumerate(result.matches, 1):
        # Format timestamps as MM:SS
        match_start_str = _fmt_timestamp(match.match_start)
        highlights_start_str = _fmt_timestamp(match.highlights_start)
        highlights_end_str = _fmt_timestamp(match.highlights_end)
        match_end_str = _fmt_timestamp(match.match_end)

        # Calculate durations (handle None values)
        intro_duration = (match.highlights_start - match.match_start
                          if match.highlights_start and match.match_start else None)
        highlights_duration = (match.highlights_end - match.highlights_start
                               if match.highlights_end and match.highlights_start else None)
        postmatch_duration = (match.match_end - match.highlights_end
                              if match.match_end and match.highlights_end else None)
        total_duration = (match.match_end - match.match_start
                          if match.match_end and match.match_start else None)

        # Reorder teams to home/away (internal storage is alphabetical)
        home_team, away_team = _get_home_away_teams(match.teams, fixtures)
        click.echo(f"Match {i}: {home_team} vs {away_team}")
        click.echo(f"\n  Strategy Results:")

        # Venue strategy
        if match.venue_result:
            venue_ts = match.venue_result.get('timestamp')
            venue_str = f"{int(venue_ts // 60):02d}:{int(venue_ts % 60):02d}"
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
        click.echo(f"    Intro:       {match_start_str} → {highlights_start_str} ({_fmt_duration(intro_duration)})")
        click.echo(f"    Highlights:  {highlights_start_str} → {highlights_end_str} ({_fmt_duration(highlights_duration)})")
        click.echo(f"    Post-match:  {highlights_end_str} → {match_end_str} ({_fmt_duration(postmatch_duration)})")
        click.echo(f"    Total:       {match_start_str} → {match_end_str} ({_fmt_duration(total_duration)})")

        # Display detection events for debugging (Task 012-03)
        _display_detection_events(match, i, result.matches)

        click.echo()


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

    # Only show section if we have events
    if events:
        click.echo(f"\n  Detection Events:")
        for event in events:
            click.echo(event)


def display_validation_summary(
    result: RunningOrderResult
) -> None:
    """
    Display strategy comparison summary statistics.

    Args:
        result: Complete running order with boundaries
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
