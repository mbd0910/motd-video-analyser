# Ground Truth Labeling Template

**Episode:** motd_2025-26_2025-11-01
**Total scenes to label:** 39
**Purpose:** Manual ground truth labels for training segment classifier
**Created:** 2025-11-18

## Instructions

Fill in the "Your labels" section for each scene below. View frames in:
`data/cache/motd_2025-26_2025-11-01/frames/`

**Segment types:**
- `intro` - Opening sequence with MOTD theme
- `studio_intro` - Host introducing next match from studio
- `highlights` - Match footage (first/second half)
- `interviews` - Post-match player/manager interviews
- `studio_analysis` - Pundits discussing match in studio
- `interlude` - MOTD2/other programme adverts
- `outro` - End credits, league table, closing montage

**Confidence levels:**
- `high` - Immediately obvious from visual/audio cues
- `medium` - Needed multiple signals to determine
- `low` - Uncertain, requires validation

---

## Intro (2 scenes)

### Scene 1 - 00:00 (2.2s)
**Pre-filled data:**
- Note: Very start of episode
- Frames available: 2
- Has OCR: NO
- OCR teams: N/A
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_0001_scene_change_0.0s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_0002_interval_sampling_2.0s.jpg

**Your labels:**
- Segment type: intro
- Confidence: high
- Visual cues: I recognise this as the start of the 2025-26 MOTD intro. As a human, I just know this is the intro!
- Notes: Will change every season, but for now this is *THE* intro.

---

### Scene 115 - 00:44 (0.9s)
**Pre-filled data:**
- Note: Near end of intro sequence
- Frames available: 0
- Has OCR: NO
- OCR teams: N/A
- Transcript: N/A (fill manually if needed)
- Frame files: N/A

**Your labels:**
- Segment type: intro
- Confidence: high
- Visual cues: Highlight from a game with no scoreboard - frames before were golazos from last season
- Notes: Can probably be inferred that we're still in the intro regardless of what's happening on screen based on timestamps alone. If we know the intro has started, and we know how long it is, we're all good.

---

## Studio Intro (7 scenes)

### Scene 124 - 00:49 (1.4s)
**Pre-filled data:**
- Note: Match 1
- Frames available: 1
- Has OCR: NO
- OCR teams: N/A
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_0040_interval_sampling_50.0s.jpg

**Your labels:**
- Segment type: intro
- Confidence: high
- Visual cues: Swirling club badges and PL logo in the middle
- Notes: This is probably the penultimate frame before the presenter appears on the screen.

---

### Scene 296 - 13:13 (92.0s)
**Pre-filled data:**
- Note: Match 2
- Frames available: 46
- Has OCR: NO
- OCR teams: N/A
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_0423_scene_change_793.1s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_0424_interval_sampling_796.0s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_0425_interval_sampling_798.0s.jpg

**Your labels:**
- Segment type: studio_analysis
- Confidence: high
- Visual cues: 3 pundits all on screen, sitting in chairs, studio backdrop. Clearly not any of the other segment types
- Notes: ___________

---

### Scene 424 - 26:22 (4.2s)
**Pre-filled data:**
- Note: Match 3
- Frames available: 2
- Has OCR: NO
- OCR teams: N/A
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_0828_interval_sampling_1584.0s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_0829_interval_sampling_1586.0s.jpg

**Your labels:**
- Segment type: studio_analyis
- Confidence: high
- Visual cues: single pundit on screen, sitting down, studio backdrop. Clearly not any of the other segment types
- Notes: ___________

---

### Scene 636 - 41:48 (1.1s)
**Pre-filled data:**
- Note: Match 4
- Frames available: 0
- Has OCR: NO
- OCR teams: N/A
- Transcript: N/A (fill manually if needed)
- Frame files: N/A

**Your labels:**
- Segment type: studio_analysis
- Confidence: high
- Visual cues: 3 pundits all on screen, sitting in chairs, studio backdrop. Clearly not any of the other segment types
- Notes: Had to be taken directly from the video

---

### Scene 800 - 52:42 (5.5s)
**Pre-filled data:**
- Note: Match 5
- Frames available: 1
- Has OCR: NO
- OCR teams: N/A
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_1638_scene_change_3162.1s.jpg

**Your labels:**
- Segment type: interlude
- Confidence: low
- Visual cues: Players from multiple teams on screens. Looks like some text is about to appear in the lower portion of the screen. Studio background based imagery at the top and bottom of the image.
- Notes: I am mostly inferring this from having watched the video in full already.

---

### Scene 932 - 64:46 (8.6s)
**Pre-filled data:**
- Note: Match 6
- Frames available: 4
- Has OCR: NO
- OCR teams: N/A
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_2007_interval_sampling_3888.0s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_2008_interval_sampling_3890.0s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_2009_interval_sampling_3892.0s.jpg

**Your labels:**
- Segment type: studio_analysis
- Confidence: high
- Visual cues: single pundit on screen, sitting down, studio backdrop. Clearly not any of the other segment types
- Notes: ___________

---

### Scene 1018 - 74:37 (3.1s)
**Pre-filled data:**
- Note: Match 7
- Frames available: 2
- Has OCR: NO
- OCR teams: N/A
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_2303_scene_change_4477.9s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_2304_interval_sampling_4480.0s.jpg

**Your labels:**
- Segment type: studio_analysis
- Confidence: high
- Visual cues: single pundit on screen, sitting down, studio backdrop. Clearly not any of the other segment types
- Notes: ___________

---

## Highlights (7 scenes)

### Scene 133 - 01:52 (16.7s)
**Pre-filled data:**
- Note: Match 1 - has OCR
- Frames available: 8
- Has OCR: YES
- OCR teams: Liverpool, Aston Villa
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_0072_interval_sampling_114.0s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_0073_interval_sampling_116.0s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_0074_interval_sampling_118.0s.jpg

**Your labels:**
- Segment type: highlights
- Confidence: high
- Visual cues: Scoreboard top left, football pitch, players, ball!
- Notes: ___________

---

### Scene 317 - 15:11 (2.8s)
**Pre-filled data:**
- Note: Match 2 - has OCR
- Frames available: 2
- Has OCR: YES
- OCR teams: Burnley, Arsenal
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_0484_interval_sampling_912.0s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_0485_interval_sampling_914.0s.jpg

**Your labels:**
- Segment type: highlights
- Confidence: medium/high
- Visual cues: Player at stadium. Graphics transition in top left - the score is partially displayed in the first frame, and completely displayed in the second frame. 
- Notes: The visual cues make it much more likely to be highlights than some sort of replay afterwards.

---

### Scene 432 - 27:25 (12.2s)
**Pre-filled data:**
- Note: Match 3 - has OCR
- Frames available: 6
- Has OCR: YES
- OCR teams: Nottingham Forest, Manchester United
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_0859_scene_change_1645.2s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_0860_interval_sampling_1648.0s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_0861_interval_sampling_1650.0s.jpg

**Your labels:**
- Segment type: highlights
- Confidence: medium/high
- Visual cues: Scoreboard in top left of 2nd and 3rd frames. First frame looks like a transition into the highlights. Football pitch, players, ball!
- Notes: The second and third frames are high - the first is medium. 

---

### Scene 642 - 42:35 (21.0s)
**Pre-filled data:**
- Note: Match 4 - has OCR
- Frames available: 10
- Has OCR: YES
- OCR teams: Fulham, Wolverhampton Wanderers
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_1335_interval_sampling_2558.0s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_1336_interval_sampling_2560.0s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_1337_interval_sampling_2562.0s.jpg

**Your labels:**
- Segment type: highlights
- Confidence: high
- Visual cues: Scoreboard top left, football pitch, players, ball!
- Notes: ___________

---

### Scene 812 - 53:36 (6.8s)
**Pre-filled data:**
- Note: Match 5 - has OCR
- Frames available: 3
- Has OCR: YES
- OCR teams: Tottenham Hotspur, Chelsea
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_1664_interval_sampling_3218.0s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_1665_interval_sampling_3220.0s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_1666_interval_sampling_3222.0s.jpg

**Your labels:**
- Segment type: highlights
- Confidence: high
- Visual cues: Scoreboard top left. No pitch in view - it's a close up of the manager but can tell its highlights because of the score being visible, and it's obvious to a human that he's watching the game.
- Notes: ___________

---

### Scene 945 - 65:46 (20.8s)
**Pre-filled data:**
- Note: Match 6 - has OCR
- Frames available: 10
- Has OCR: YES
- OCR teams: Brighton & Hove Albion, Leeds United
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_2037_interval_sampling_3948.0s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_2038_interval_sampling_3950.0s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_2039_interval_sampling_3952.0s.jpg

**Your labels:**
- Segment type: highlights
- Confidence: medium/high
- Visual cues: No scoreboard visible in the frame files you've listed, but if I watch the video for 20.8 seconds it shortly comes into view. The classic signs that it's highlights are all there though - pitch, players, ball!
- Notes: ___________

---

### Scene 1028 - 75:26 (11.2s)
**Pre-filled data:**
- Note: Match 7 - has OCR
- Frames available: 6
- Has OCR: YES
- OCR teams: Crystal Palace, Brentford
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_2329_interval_sampling_4528.0s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_2330_interval_sampling_4530.0s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_2331_interval_sampling_4532.0s.jpg

**Your labels:**
- Segment type: highlights
- Confidence: high
- Visual cues: No scoreboard visible in first frame file you've listed, but the transition animation in the top left has *just* started, so we see the scoreboard in the subsequent frames. Pitch, players, ball all visible.
- Notes: ___________

---

## Interviews (5 scenes)

### Scene 272 - 10:08 (2.8s)
**Pre-filled data:**
- Note: Match 1
- Frames available: 1
- Has OCR: NO
- OCR teams: N/A
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_0330_interval_sampling_610.0s.jpg

**Your labels:**
- Segment type: highlights (see notes below)
- Confidence: medium
- Visual cues: From checking the video, it's super obvious this is definitely the last frame before the interviews. The full time graphic has just been displayed, and we haven't yet transitioned to the interviews. But from a still frame it's not at all obvious where we are here - this could easily be highlights or a clip during the studio analysis. It's a player on the pitch, so I don't think this could be interpreted as interviews yet.
- Notes: ___________

---

### Scene 403 - 22:05 (3.8s)
**Pre-filled data:**
- Note: Match 2
- Frames available: 2
- Has OCR: YES
- OCR teams: Burnley, Arsenal
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_0697_scene_change_1325.4s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_0698_interval_sampling_1328.0s.jpg

**Your labels:**
- Segment type: highlights
- Confidence: high
- Visual cues: This is the very end of the highlights for this game - the FT graphic is visible in both frames.
- Notes: ___________

---

### Scene 601 - 35:24 (1.0s)
**Pre-filled data:**
- Note: Match 3
- Frames available: 0
- Has OCR: NO
- OCR teams: N/A
- Transcript: N/A (fill manually if needed)
- Frame files: N/A

**Your labels:**
- Segment type: highlights
- Confidence: high
- Visual cues: This is the very end of the highlights for this game - the FT graphic is visible in the video at this timestamp.
- Notes: ___________

---

### Scene 734 - 48:01 (5.0s)
**Pre-filled data:**
- Note: Match 4
- Frames available: 3
- Has OCR: YES
- OCR teams: Fulham, Wolverhampton Wanderers
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_1502_scene_change_2881.3s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_1503_interval_sampling_2884.0s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_1504_interval_sampling_2886.0s.jpg

**Your labels:**
- Segment type: highlights
- Confidence: high
- Visual cues: This is the very end of the highlights for this game - the FT graphic is visible in the video at this timestamp. Players congratulating each other on the pitch.
- Notes: ___________

---

### Scene 907 - 60:43 (5.6s)
**Pre-filled data:**
- Note: Match 5
- Frames available: 3
- Has OCR: YES
- OCR teams: Tottenham Hotspur, Chelsea
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_1884_scene_change_3643.6s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_1885_interval_sampling_3646.0s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_1886_interval_sampling_3648.0s.jpg

**Your labels:**
- Segment type: highlights
- Confidence: high
- Visual cues: This is the very end of the highlights for this game - the FT graphic is visible in the video at this timestamp. Players congratulating each other on the pitch.
- Notes: ___________

---

## Studio Analysis (7 scenes)

### Scene 287 - 10:49 (14.7s)
**Pre-filled data:**
- Note: Match 1
- Frames available: 7
- Has OCR: NO
- OCR teams: N/A
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_0352_interval_sampling_652.0s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_0353_interval_sampling_654.0s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_0354_interval_sampling_656.0s.jpg

**Your labels:**
- Segment type: interviews
- Confidence: high
- Visual cues: Aston Villa manager Unai Emery (I recognise him) is taking up a majority of the screen (his head, shoulders: chest upwards basically). He's standing in front of a microphone and behind him are lots of sponsor logos.
- Notes: ___________

---

### Scene 412 - 22:50 (6.6s)
**Pre-filled data:**
- Note: Match 2
- Frames available: 4
- Has OCR: NO
- OCR teams: N/A
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_0720_scene_change_1370.8s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_0721_interval_sampling_1372.0s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_0722_interval_sampling_1374.0s.jpg

**Your labels:**
- Segment type: interviews
- Confidence: high
- Visual cues: Arsenal manager Mikel Arteta (I recognise him) is taking up a majority of the screen (his head, shoulders: chest upwards basically). He's standing in front of a microphone and behind him are lots of sponsor logos. 
- Notes: ___________

---

### Scene 611 - 36:13 (25.7s)
**Pre-filled data:**
- Note: Match 3
- Frames available: 13
- Has OCR: NO
- OCR teams: N/A
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_1142_scene_change_2173.7s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_1143_interval_sampling_2176.0s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_1144_interval_sampling_2178.0s.jpg

**Your labels:**
- Segment type: interviews
- Confidence: high
- Visual cues: Nottingham Forest manager Sean Dyche is taking up a majority of the screen (his head, shoulders: chest upwards basically). He's standing in front of a microphone and behind him are lots of sponsor logos. His name is displayed in the lower left corner in frame_1143.
- Notes: ___________

---

### Scene 750 - 49:35 (9.5s)
**Pre-filled data:**
- Note: Match 4
- Frames available: 5
- Has OCR: NO
- OCR teams: N/A
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_1549_scene_change_2975.5s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_1550_interval_sampling_2978.0s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_1551_interval_sampling_2980.0s.jpg

**Your labels:**
- Segment type: interviews
- Confidence: high
- Visual cues: Wolves manager is taking up a majority of the screen (his head, shoulders: chest upwards basically). He's standing in front of a microphone and behind him are lots of sponsor logos.
- Notes: ___________

---

### Scene 920 - 61:37 (6.6s)
**Pre-filled data:**
- Note: Match 5
- Frames available: 4
- Has OCR: NO
- OCR teams: N/A
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_1911_scene_change_3697.6s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_1912_interval_sampling_3700.0s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_1913_interval_sampling_3702.0s.jpg

**Your labels:**
- Segment type: studio_analysis
- Confidence: high
- Visual cues: Zomomed out view of pitch and stadium, cutting to image of 3 pundits in the studio sitting in their chairs with MOTD studio background in view. No scoreboard suggests no highlights.
- Notes: ___________

---

### Scene 1007 - 72:05 (24.3s)
**Pre-filled data:**
- Note: Match 6
- Frames available: 13
- Has OCR: NO
- OCR teams: N/A
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_2227_scene_change_4325.7s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_2228_interval_sampling_4328.0s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_2229_interval_sampling_4330.0s.jpg

**Your labels:**
- Segment type: interviews
- Confidence: high
- Visual cues: Brighton manager Fabian Hurzeler is taking up a majority of the screen (his head, shoulders: chest upwards basically). He's standing in front of a microphone and behind him are lots of sponsor logos. His name is displayed in the lower left corner in frame_2228.
- Notes: ___________

---

### Scene 1177 - 81:48 (2.6s)
**Pre-filled data:**
- Note: Match 7
- Frames available: 1
- Has OCR: NO
- OCR teams: N/A
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_2529_interval_sampling_4910.0s.jpg

**Your labels:**
- Segment type: interviews
- Confidence: high
- Visual cues: Palace manager Oliver Glasner is taking up a majority of the screen (his head, shoulders: chest upwards basically). He's standing in front of a microphone and behind him are lots of sponsor logos.
- Notes: ___________

---

## Interlude (2 scenes)

### Scene 765 - 51:58 (2.9s)
**Pre-filled data:**
- Note: Start of MOTD2 interlude
- Frames available: 2
- Has OCR: NO
- OCR teams: N/A
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_1621_scene_change_3118.5s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_1622_interval_sampling_3120.0s.jpg

**Your labels:**
- Segment type: intro / studio_intro / studio_analysis / interlude / outro
- Confidence: low
- Visual cues: Single pundit looking into the camera in front of BBC MOTD studio background.
- Notes: From the still images, it's almost impossible to determine what this segment is - it could be an introduction to the whole program, an individual match or the interlude. From the video I *know* it's the interlude, but that's not obvious from these still images.

---

### Scene 793 - 52:19 (0.1s)
**Pre-filled data:**
- Note: Mid MOTD2 interlude
- Frames available: 0
- Has OCR: NO
- OCR teams: N/A
- Transcript: N/A (fill manually if needed)
- Frame files: N/A

**Your labels:**
- Segment type: interlude
- Confidence: low
- Visual cues: Stadium footage. Keeper watching ball creep into net.
- Notes: From the video this is obvious based on what's come before it, but from an individual image/frame, it's very hard to tell - this could easily be from the highlights or studio analysis.

---

## Outro (2 scenes)

### Scene 1195 - 82:56 (2.4s)
**Pre-filled data:**
- Note: Start of outro
- Frames available: 1
- Has OCR: NO
- OCR teams: N/A
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_2566_interval_sampling_4978.0s.jpg

**Your labels:**
- Segment type: intro / studio_intro / studio_analysis / interlude / outro
- Confidence: low
- Visual cues: Single pundit looking into the camera in front of BBC MOTD studio background.
- Notes: From the still images, it's almost impossible to determine what this segment is - it could be an introduction to the whole program, an individual match or the interlude. From the video I *know* it's the interlude, but that's not obvious from these still images.
---

### Scene 1229 - 83:55 (4.1s)
**Pre-filled data:**
- Note: End of episode
- Frames available: 2
- Has OCR: NO
- OCR teams: N/A
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_2598_scene_change_5035.2s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_2599_interval_sampling_5038.0s.jpg

**Your labels:**
- Segment type: outro
- Confidence: high
- Visual cues: BBC logo in front of black background. MMXXV text.
- Notes: ___________

---

## Transitions (6 scenes)

### Scene 194 - 05:02 (0.4s)
**Pre-filled data:**
- Note: SECOND HALF indicator
- Frames available: 0
- Has OCR: NO
- OCR teams: N/A
- Transcript: N/A (fill manually if needed)
- Frame files: N/A

**Your labels:**
- Segment type: highlights
- Confidence: high
- Visual cues: Scoreboard in top left. Player celebrating a goal.
- Notes: Taken directly from video

---

### Scene 357 - 18:31 (1.8s)
**Pre-filled data:**
- Note: SECOND HALF indicator
- Frames available: 0
- Has OCR: NO
- OCR teams: N/A
- Transcript: N/A (fill manually if needed)
- Frame files: N/A

**Your labels:**
- Segment type: highlights
- Confidence: high
- Visual cues: Scoreboard in top left. Players, pitch, ball!
- Notes: ___________

---

### Scene 462 - 28:43 (4.3s)
**Pre-filled data:**
- Note: SECOND HALF indicator
- Frames available: 2
- Has OCR: YES
- OCR teams: Nottingham Forest, Manchester United
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_0903_scene_change_1723.2s.jpg, data/cache/motd_2025-26_2025-11-01/frames/frame_0904_interval_sampling_1726.0s.jpg

**Your labels:**
- Segment type: highlights
- Confidence: high
- Visual cues: Scoreboard in top left. Players, pitch, ball!
- Notes: ___________

---

### Scene 588 - 34:31 (0.2s)
**Pre-filled data:**
- Note: SECOND HALF indicator
- Frames available: 1
- Has OCR: YES
- OCR teams: Nottingham Forest, Manchester United
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_1089_scene_change_2071.1s.jpg

**Your labels:**
- Segment type: highlights
- Confidence: high
- Visual cues: Scoreboard in top left. Ball in the goal - someone has just scored.
- Notes: ___________

---

### Scene 666 - 44:39 (0.2s)
**Pre-filled data:**
- Note: SECOND HALF indicator
- Frames available: 1
- Has OCR: NO
- OCR teams: N/A
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_1396_scene_change_2679.3s.jpg

**Your labels:**
- Segment type: highlights
- Confidence: high
- Visual cues: Huge second half graphic / transition on screen. We must be half way through the highlights for this game.
- Notes: ___________

---

### Scene 729 - 47:59 (0.3s)
**Pre-filled data:**
- Note: SECOND HALF indicator
- Frames available: 1
- Has OCR: NO
- OCR teams: N/A
- Transcript: N/A (fill manually if needed)
- Frame files: data/cache/motd_2025-26_2025-11-01/frames/frame_1501_scene_change_2879.5s.jpg

**Your labels:**
- Segment type: highlights
- Confidence: medium
- Visual cues: Managers are visible in the ground with crowd behind them. From the still iamge this is probably the beginning or end of the highlights package. From the video I can tell it's the end as the FT graphic has just been displayed.
- Notes: ___________

---

