/** Mirrors Python EpisodeAnalysis and related models from src/motd/models.py */

export interface IndexEntry {
  episode_id: string;
  broadcast_date: string;
  season: string;
  match_count: number;
}

export interface EpisodeIndex {
  episodes: IndexEntry[];
}

export interface Score {
  home: number;
  away: number;
}

export interface Segment {
  start: string | null;
  end: string | null;
}

export interface MatchCoverage {
  order: number;
  home_team: string;
  away_team: string;
  venue: string;
  score: Score;
  segments: Record<string, Segment>;
  notes: string | null;
}

export interface EpisodeAnalysis {
  episode_id: string;
  broadcast_date: string;
  season: string;
  matches: MatchCoverage[];
}
