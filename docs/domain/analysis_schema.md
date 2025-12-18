# LLM Analysis Output Schema

> **Last reviewed:** 2025-12-18

This document defines the JSON structure for LLM-analysed episode data.

## Storage Location

```
data/analysis/{episode_id}/analysis.json
```

Example: `data/analysis/motd_2025-26_2025-11-22/analysis.json`

## Workflow

1. Run `python -m motd generate-llm-prompt <episode_id>`
2. Copy the generated prompt to Claude web UI
3. Copy Claude's JSON response
4. Save to `data/analysis/{episode_id}/analysis.json`
5. Commit to source control

## JSON Schema

```json
{
  "episode": {
    "date": "YYYY-MM-DD",
    "intro": {
      "start": "MM:SS",
      "end": "MM:SS"
    },
    "league_table": {
      "start": "MM:SS",
      "end": "MM:SS"
    },
    "next_motd_promo": {
      "start": "MM:SS",
      "end": "MM:SS"
    },
    "outro": {
      "start": "MM:SS",
      "end": "MM:SS"
    }
  },
  "matches": [
    {
      "order": 1,
      "home_team": "Team Name",
      "away_team": "Team Name",
      "venue": "Stadium Name",
      "score": {
        "home": 0,
        "away": 0
      },
      "segments": {
        "studio_intro": {
          "start": "MM:SS",
          "end": "MM:SS"
        },
        "lineups": {
          "start": "MM:SS",
          "end": "MM:SS"
        },
        "highlights": {
          "start": "MM:SS",
          "end": "MM:SS"
        },
        "post_match_interviews": {
          "start": "MM:SS",
          "end": "MM:SS"
        },
        "studio_analysis": {
          "start": "MM:SS",
          "end": "MM:SS"
        }
      },
      "notes": "Any observations or edge cases"
    }
  ]
}
```

## Field Definitions

### Episode-Level Segments

| Field | Description | Required |
|-------|-------------|----------|
| `date` | Broadcast date (YYYY-MM-DD) | Yes |
| `intro` | Opening sequence with pundit introductions | Yes |
| `league_table` | League standings review segment | No (null if absent) |
| `next_motd_promo` | Promo for next MOTD episode | No (null if absent) |
| `outro` | Closing credits/sign-off | No (null if absent) |

### Match Segments

| Field | Description | Required |
|-------|-------------|----------|
| `order` | Running order position (1 = first match shown) | Yes |
| `home_team` | Home team name (as shown in MOTD) | Yes |
| `away_team` | Away team name | Yes |
| `venue` | Stadium name | Yes |
| `score` | Final score `{home: N, away: N}` | Yes |
| `segments.studio_intro` | Pundit discussion before highlights | Yes |
| `segments.lineups` | Formation graphics and team walkthrough | No |
| `segments.highlights` | Match footage with commentary | Yes |
| `segments.post_match_interviews` | Pitchside interviews | No |
| `segments.studio_analysis` | Post-match pundit discussion | No |
| `notes` | Edge cases or observations | No |

### Timestamp Format

- Format: `MM:SS` (e.g., "12:30" for 12 minutes 30 seconds)
- Both `start` and `end` can independently be `null` if unclear
- Example: `{"start": "12:30", "end": null}` means start is known but end is unclear

## Segment Boundary Definitions

### studio_intro
- **STARTS**: When pundits begin discussing the upcoming match
- **ENDS**: At commentator credit ("Your commentator, [name]" or "[name] was at [venue]")

### lineups
- **STARTS**: After commentator credit
- **ENDS**: When actual match action begins (scoreboard appears)

### highlights
- **STARTS**: When match action begins (scoreboard visible)
- **ENDS**: At full-time announcement or transition to interviews

### post_match_interviews
- **STARTS**: When interview begins (player/manager pitchside)
- **ENDS**: When returning to studio

### studio_analysis
- **STARTS**: When pundits return to discuss the match
- **ENDS**: When moving to next match or episode segment
