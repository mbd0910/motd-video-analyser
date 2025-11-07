# Match of the Day Analyser - Product Requirements Document

## 1. Project Overview

### Vision
Build an automated video analysis pipeline to objectively measure potential coverage bias in BBC's Match of the Day, settling age-old football fan debates with data rather than perception.

### Goals
- Extract structured data from MOTD episodes: running order, airtime distribution, post-match analysis patterns
- Create reproducible, auditable analysis that stands up to scrutiny
- Generate clean JSON output for integration into blog posts and visualisations
- Build an extensible pipeline that can be adapted for other video content (podcasts, other football shows)

### Success Criteria
- Successfully analyse all 10 MOTD episodes from the 2025/26 season
- Achieve >95% accuracy on team identification (using fixture-aware matching)
- Achieve >95% accuracy on timestamp detection
- Processing time: overnight batch processing acceptable (8-12 hours for 10 episodes)
- Output data is manually verifiable against source videos

### Out of Scope (Version 1)
- MOTD2 coverage
- Historical seasons (2023/24 and earlier)
- Real-time or live processing
- Sentiment analysis of commentary
- Automated video editing or highlight generation

---

## 2. User Personas

### The Builder (You - Michael)

**Background**: Software engineer with 20 years experience, heavy football/sports betting background, Charlton Athletic supporter for 36 years, currently building audience as independent creator.

**Technical Profile**:
- Comfortable with Python, data analysis, system architecture
- AI power user leveraging Claude Code for spec-driven development
- Capable of code review, system design, and manual data validation

**Needs**:
- Accurate, reproducible data pipeline that produces defensible results
- Clean JSON output for easy integration into blog posts
- Modular, maintainable codebase that can be extended to other projects
- Ability to validate results manually before publishing

**Success Looks Like**:
- Can confidently publish analysis knowing the data is sound
- Can showcase both football knowledge and technical expertise
- Has a reusable pipeline for future video/audio content projects

---

### The Audiences (Content Consumers)

**Football Analytics Audience**
- **Who**: Football fans, sports journalists, data enthusiasts
- **What they want**: Answers to "is there really bias?" with data to back it up
- **Content they'll consume**: Blog posts with findings, charts, pattern analysis
- **What they don't care about**: How the pipeline works technically

**Technical Showcase Audience**
- **Who**: Software engineers, data engineers, AI/ML practitioners, potential collaborators/clients
- **What they want**: Learn how to build video analysis pipelines, see real-world AI application
- **Content they'll consume**: Technical deep-dives, architecture docs, GitHub repo
- **What they don't care about**: Specific football insights (though might find them interesting)

---

## 3. Core Features & Requirements

### 3.1 Match Running Order Detection
**Description**: Identify the sequence in which matches appear in each episode.

**Requirements**:
- Detect when a new match segment begins
- Extract team names for each match
- Assign sequential running order (1st, 2nd, 3rd, etc.)
- Handle variable number of matches per episode (typically 5-8 matches)

**Technical Approach**:
- Scene detection to identify transitions
- OCR on scoreboard graphics (top-left corner, bottom-right formation graphics)
- Cross-reference detected teams against fixture data for episode date
- Validate using known fixtures to improve accuracy and correct OCR errors

---

### 3.2 Airtime Calculation (Segmented)
**Description**: Calculate time allocated to each match, broken down by segment type.

**Requirements**:
- Track total airtime per match
- Segment breakdown:
  - Studio introduction (pundit talk before highlights)
  - Match highlights (gameplay footage)
  - Interviews (post-match player/manager interviews)
  - Studio analysis (pundit discussion after highlights)

**Technical Approach**:
- Scene classification: studio vs. match footage vs. interview
- Interview detection: single face occupying majority of frame
- Timestamp each segment start/end
- Calculate durations

**Edge Cases**:
- **Studio-Based Remote Interviews**: Sometimes conducted in studio via video link (large screen visible, or split-screen)
  - Visual pattern: Studio background + pundit(s) + screen showing interviewee
  - Classify as "interview" segment with optional location metadata
  - May distinguish in output: `interview_pitchside` vs `interview_studio_remote`

---

### 3.3 First Team Mentioned in Analysis
**Description**: Identify which team is discussed first during post-match studio analysis.

**Requirements**:
- Transcribe audio from studio analysis segments only
- Identify first team name mentioned after returning to studio
- Handle edge cases: team mentioned in passing vs. substantive discussion
- Note: Initial version captures chronological first mention; future version may weight by discussion depth

**Technical Approach**:
- Use Whisper (local) for speech-to-text
- Pattern matching against team name list (full names + abbreviations)
- Timestamp of first mention

---

### 3.4 JSON Data Export
**Description**: Output structured data for blog integration.

**Format**:
```json
{
  "episode_date": "2024-08-17",
  "episode_duration": "01:22:45",
  "total_matches": 6,
  "matches": [
    {
      "running_order": 1,
      "fixture_id": "2024-08-16-manutd-fulham",
      "teams": ["Manchester United", "Fulham"],
      "home_team": "Manchester United",
      "away_team": "Fulham",
      "segments": [
        {
          "type": "studio_intro",
          "start": "00:01:30",
          "end": "00:02:15",
          "duration_seconds": 45
        },
        {
          "type": "highlights",
          "start": "00:02:15",
          "end": "00:08:30",
          "duration_seconds": 375
        },
        {
          "type": "interview",
          "location": "pitchside",
          "start": "00:08:30",
          "end": "00:10:00",
          "duration_seconds": 90
        },
        {
          "type": "studio_analysis",
          "start": "00:10:00",
          "end": "00:13:45",
          "duration_seconds": 225,
          "first_team_mentioned": "Manchester United",
          "transcript_snippet": "So Gary, what did you make of United's performance..."
        }
      ],
      "total_airtime_seconds": 735,
      "confidence": {
        "teams": 0.95,
        "timestamp": 0.99,
        "segment_type": 0.85
      },
      "fixture_validated": true
    }
  ],
  "metadata": {
    "processed_date": "2024-11-06",
    "pipeline_version": "0.1.0",
    "manual_validation": false
  }
}
```

---

## 4. Success Metrics

### Data Quality Metrics (Validation Phase)
These metrics are for **establishing trust** in the pipeline during initial validation (first 1-2 episodes). Once validated, the pipeline should run unattended on remaining episodes.

- **Team Identification Accuracy**: >95% correct team detection using fixture-aware matching (fixture context provides 5-10% improvement over OCR-only)
- **Timestamp Accuracy**: >95% accurate scene transition detection (±2 seconds acceptable)
- **Segment Classification**: >85% correct classification of segment types (studio/highlights/interview/analysis)

**Trust Threshold**: If the pipeline hits these metrics on 2 consecutive episodes with manual validation, it's production-ready for batch processing the remaining episodes without manual review.

**Note**: As a perfectionist, you may be tempted to validate every episode. Resist this urge - the point is to build a system you can trust to run autonomously.

---

### Performance Metrics
- **Processing Speed**: 1-2 hours per 90-minute episode (acceptable for batch processing)
- **Batch Processing**: All 10 episodes processable overnight (8-12 hours total)
- **Resource Usage**: Runnable on local machine (M3 Pro MacBook with 36GB RAM)

---

### Usability Metrics
- **Manual Validation Time**: <30 minutes to spot-check one episode's output
- **Data Export**: JSON files ready for blog integration without transformation
- **Pipeline Re-runs**: Can re-process episode with different parameters in <30 minutes

---

### Reliability Metrics
- **Reproducibility**: Running pipeline twice on same video produces identical results
- **Failure Handling**: Pipeline continues if one match segment fails; logs errors clearly
- **Data Completeness**: Every match has at minimum: teams, running order, total airtime

---

## 5. User Stories & Acceptance Criteria

### Story 1: Extract Match Running Order
**As** the analyst
**I want** to automatically detect the sequence of matches in an episode
**So that** I can analyse whether certain teams are consistently placed first/last

**Acceptance Criteria**:
- [ ] Pipeline outputs running order (1, 2, 3...) for each match
- [ ] Team names are correctly identified for each match
- [ ] Running order matches manual review of the video
- [ ] Handles episodes with 5-8 matches

---

### Story 2: Calculate Segmented Airtime
**As** the analyst
**I want** to know how much time each match gets, broken down by segment type
**So that** I can compare not just total coverage, but quality of coverage (highlights vs. analysis)

**Acceptance Criteria**:
- [ ] Each match has total airtime calculated
- [ ] Airtime broken down into: studio_intro, highlights, interview, studio_analysis
- [ ] Timestamps are accurate to within 2 seconds
- [ ] Durations sum correctly (segment durations = total airtime)

---

### Story 3: Identify First Team Mentioned in Analysis
**As** the analyst
**I want** to know which team is discussed first in post-match analysis
**So that** I can detect potential focus bias in punditry

**Acceptance Criteria**:
- [ ] Studio analysis segments are transcribed
- [ ] First team mention is identified and timestamped
- [ ] Handles team name variations (full name, abbreviations, nicknames)
- [ ] Includes transcript snippet for manual verification

---

### Story 4: Manual Validation Workflow
**As** the analyst
**I want** to validate and correct the pipeline's output for the first video
**So that** I can establish ground truth and tune the system

**Acceptance Criteria**:
- [ ] Pipeline outputs scene transitions with timestamps to JSON
- [ ] I can review and label each scene with type (studio/highlights/interview/analysis)
- [ ] I can add/correct team names where OCR fails
- [ ] Corrected data can be used to validate pipeline accuracy

---

## 6. Technical Constraints & Requirements

### Environment
- **Python Version**: 3.12.7
- **Platform**: macOS (M3 Pro MacBook, 36GB RAM)
- **Dependency Management**: pip with requirements.txt
- **System Dependencies**: ffmpeg (to be installed)

### Video Specifications
- **Format**: MP4 (downloaded via yt-dlp from BBC iPlayer)
- **Quality**: ~3.35GB for 83 minutes (~5.5 Mbps bitrate, likely 720p or 1080p)
- **Typical Duration**: 60-90 minutes per episode
- **Volume**: 10 episodes for initial analysis

### Processing Constraints
- **Local Processing**: Must run on local machine (no cloud dependency)
- **Overnight Processing**: Batch processing 8-12 hours for all episodes is acceptable
- **GPU**: M3 Pro will be leveraged for Whisper transcription

---

## 7. Data Requirements

### Input Data
- **Premier League Team Names**: JSON file with full names, abbreviations, 3-letter codes, nicknames
  - Example: `{"full": "Manchester United", "abbrev": "Man Utd", "code": "MUN", "alternates": ["United", "Man United"]}`
- **Premier League Fixtures**: JSON file with match schedules for the season
  - Fields: date, home_team, away_team, kickoff_time, final_score (venue optional)
  - Example: `{"match_id": "2025-08-16-manutd-fulham", "date": "2025-08-16", "home_team": "Manchester United", "away_team": "Fulham", "kickoff": "20:00"}`
  - Used to validate OCR results and improve accuracy by limiting search space to expected matches
- **Episode Manifest**: JSON mapping video files to broadcast dates and expected fixtures
  - Links each episode to specific gameweek fixtures
  - Includes video source URL for future automation
- **Video Files**: Local paths to MP4 files

### Intermediate Data (Cached)
- **Scene Transitions**: JSON with timestamps of detected transitions
- **OCR Results**: Raw text extraction from frames
- **Fixture Matches**: JSON linking detected teams to fixture data
- **Transcripts**: Full Whisper transcription with timestamps
- **Manual Labels**: Your validation/corrections for first video

### Output Data
- **Final Analysis**: JSON per episode (schema defined in Section 3.4)
- **Validation Reports**: Comparison of automated vs. manual labels
- **Error Logs**: Any failures or low-confidence detections

---

## 8. Future Extensibility Considerations

### Potential Future Enhancements (Not v1)
- **MOTD2 Coverage**: Extend to Sunday night show
- **Historical Analysis**: Process previous seasons
- **Lower League Coverage**: Championship, League One, League Two highlights shows
- **Podcast Analysis**: Audio-only football content (e.g., The Totally Football Show, Football Weekly)
  - Remove video processing modules
  - Keep transcription and team mention analysis
  - Analyse time spent discussing each team/match
- **Sentiment Analysis**: Analyse tone of commentary/analysis per team
- **Automated Insights**: Generate summary statistics, bias scores
- **Dashboard**: Interactive visualisation of results

### Design Principles for Extensibility
- **Modular Pipeline**: Each stage (scene detection, OCR, transcription) operates independently
- **Configurable Team Lists**: Easy to swap Premier League teams for Championship/League One teams
- **Audio-First Design**: Structure transcription/analysis to work without video dependency
- **Format Agnostic**: JSON output can feed any frontend (blog, dashboard, social media graphics)

---

## 9. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| OCR fails on team names | Medium | Medium | Fixture-aware matching corrects OCR errors; manual labels for first video |
| Scene detection misses transitions | High | Medium | Tune threshold parameters; validate on first video |
| Whisper transcription inaccurate | Medium | Low | Use largest Whisper model that fits in memory; spot-check transcripts |
| Processing time too long | Low | Medium | Process overnight; optimise if needed after benchmarking |
| BBC changes graphics format mid-season | Medium | Low | Modular design allows updating OCR targets without full rewrite |
| Interview detection fails (studio vs pitchside) | Medium | Medium | Manual labeling for first video; refine classifier based on patterns |
| Fixture data incorrect or incomplete | Low | Low | Manual data entry allows verification; can override with manual labels |

---

## 10. Open Questions

1. **Multiple Interviews per Match**: If there are 2+ interviews (manager + player), track separately or combine?
   - Initial: Combine as single interview segment

2. **Half-Time Analysis**: Some episodes have mid-match studio breaks - include in analysis?
   - Initial: Focus on post-match only, flag for future consideration

3. **Team Name Normalization**: How to handle "Man Utd" vs "Manchester United" vs "United"?
   - Use canonical name in output, but match all variants in OCR/transcription
