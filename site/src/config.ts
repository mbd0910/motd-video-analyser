/**
 * Base URL for the R2 bucket where episode data is stored.
 * Set via PUBLIC_R2_URL environment variable at build time.
 * Falls back to relative /data/ path for local development.
 */
export const R2_BASE_URL: string =
  import.meta.env.PUBLIC_R2_URL ?? '/data';
