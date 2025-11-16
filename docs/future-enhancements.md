# Future Enhancements

This document tracks post-MVP improvements, nice-to-haves identified during development, and technical debt to address later.

**Status:** Living document - add items as they're discovered during implementation

---

## Enhancement 001: Player Name Transcription Accuracy

**Category:** Transcription Quality
**Priority:** Low (post-MVP)
**Effort:** 1-2 hours
**Identified:** Task 010f validation (2025-11-16)
**Status:** Documented, not scheduled

### Problem

Player names in transcripts have phonetic spelling variations due to non-English orthography:
- Gravenberch → "Dravenberg"
- Caicedo → "Casedo"
- Fernández → "Fernandes"

Current accuracy: **25%** (1/4 correct in validation sample)

### Impact

**Low** - Player names are not used in current MOTD airtime analysis:
- Running order detection relies on team names (100% accurate)
- Airtime calculations use team names (100% accurate)
- Studio analysis classification uses pundit names (100% accurate)
- Player names only affect transcript readability, not analysis output

### Solution Approach

Add EPL squad custom vocabulary to faster-whisper using the `hotwords` parameter:

```python
# In src/motd/transcription/transcriber.py

def load_squad_hotwords() -> list[str]:
    """Load EPL squad names as custom vocabulary for transcription."""
    with open('data/teams/premier_league_2025_26.json') as f:
        teams_data = json.load(f)

    hotwords = []
    for team in teams_data['teams']:
        for player in team.get('squad', []):
            # Add common name (e.g., "Gravenberch", "Salah")
            hotwords.append(player['common_name'])

    return hotwords

# In transcribe() method:
hotwords = load_squad_hotwords()
segments = self.model.transcribe(
    audio_path,
    hotwords=hotwords,  # ← Add custom vocabulary
    language="en",
    ...
)
```

### Data Requirements

Extend `data/teams/premier_league_2025_26.json` with squad rosters:

```json
{
  "teams": [
    {
      "name": "Liverpool",
      "alternate_names": ["The Reds"],
      "squad": [
        {"name": "Alisson Becker", "common_name": "Alisson"},
        {"name": "Andrew Robertson", "common_name": "Robertson"},
        {"name": "Ryan Gravenberch", "common_name": "Gravenberch"},
        {"name": "Mohamed Salah", "common_name": "Salah"},
        ...
      ]
    },
    ...
  ]
}
```

**Data Source:** Premier League official squad lists or transfermarkt.com
**Maintenance:** Update twice per season (August, January transfer window)

### Expected Improvement

- Player name accuracy: **25% → 85-95%** (estimated)
- No degradation expected on other transcription quality
- Zero impact on team/pundit name accuracy (already 100%)

### Risks

1. **Over-application:** Hotwords might force player names where inappropriate (low risk - names rarely appear out of context)
2. **Maintenance burden:** Squad lists need seasonal updates (mitigated by ~500 names, 2× per year)
3. **Testing required:** Must validate improvement > degradation before deployment

### Implementation Checklist

When implementing this enhancement:

- [ ] Extend `data/teams/premier_league_2025_26.json` with squad data
- [ ] Implement `load_squad_hotwords()` in transcriber.py
- [ ] Add `hotwords` parameter to transcription call
- [ ] Re-run Task 010f validation on same 20 segments
- [ ] Compare before/after player name accuracy
- [ ] Validate no degradation on team/pundit names
- [ ] Update documentation with maintenance schedule
- [ ] Create data update process for January transfer window

### When to Implement

**Trigger conditions:**
1. User requests player-level analysis features (e.g., "which players are mentioned most?")
2. Transcript exports are used for reading (not just analysis)
3. Player name errors cause confusion in manual validation
4. Post-MVP refinement phase with available time

**Do NOT implement if:**
- Still in MVP development (current phase)
- OCR already provides sufficient player name data
- No user need for player-level analysis emerges

### References

- Validation report: `docs/validation/010f_accuracy_validation.md`
- faster-whisper hotwords docs: [CTranslate2 Whisper documentation](https://github.com/SYSTRAN/faster-whisper)
- Task 010f: `docs/tasks/010-transcription/010f-validation.md`

---

## Enhancement Template (For Future Items)

**Category:** (Transcription / OCR / Analysis / Performance / UX)
**Priority:** (High / Medium / Low)
**Effort:** (hours or story points)
**Identified:** (Task number + date)
**Status:** (Documented / Scheduled / In Progress / Complete)

### Problem
_(What issue or opportunity was identified?)_

### Impact
_(How does this affect the system or user experience?)_

### Solution Approach
_(High-level implementation strategy)_

### Expected Improvement
_(Quantifiable benefits)_

### Risks
_(Potential downsides or complications)_

### When to Implement
_(Conditions that would trigger prioritizing this enhancement)_

---

## Future Items (Placeholder)

As you progress through tasks, add new enhancements here using the template above.

Ideas might include:
- Scene detection threshold auto-tuning
- OCR region adaptive detection (for different video resolutions)
- Parallel processing for batch operations
- Cloud transcription API fallback
- Interactive validation UI
- Automated accuracy regression testing
- etc.
