# MOTD Analyser - Project Setup

I want to build a Python-based analyser for Match of the Day videos to objectively measure potential coverage bias. This is the first iteration - keep it simple and pragmatic.

## Project Goals

1. Identify the running order of matches in each episode
2. Detect which team is mentioned first in post-match analysis
3. Calculate time given to each match
4. Export results as JSON for later use in a Next.js blog

## Technical Approach suggested by Claude in the browser

- **Scene Detection**: Use OpenCV to detect transitions between matches (scoreboard graphics, studio vs match footage)
- **Team Identification**: Use Tesseract OCR to read team names from scoreboard graphics
- **Speech Analysis**: Use OpenAI's Whisper to transcribe studio segments and identify first team mentioned
- **Output**: Generate JSON files with timestamps, teams, and airtime data

**Critical**: Strongly disagree with any of these libraries if you think there are better options.

## Project Structure

Based on the libraries we choose, create a clea, single-purpose project.

## Implementation Notes

- Cache intermediate results (scene timestamps, transcripts) to avoid re-processing
- Each stage should save its output as JSON
- Start with scene detection first - we can tune and validate before adding complexity
- Use simple threshold-based scene detection initially
- Don't over-engineer - this is MVP validation mode

## First Steps

1. Set up the project structure
2. Create a basic scene detector that identifies significant frame changes
3. Run it on a test video and output timestamps of detected changes
4. Save results to JSON so I can validate manually

Let me know when you're ready and I'll provide the path to my first MOTD video file.

## Approach

* Create a step-by-step, phased approach to tackle this task.
* Ask clarifying product questions to ensure we don't dive into coding before we've fully captured what we need to do. It would be better to spend longer planning than diving into the code before we're ready.