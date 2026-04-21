// Hand-written types mirroring supabase/migrations/*.sql. Keep in sync manually when schema changes.

export type Tier = "underground" | "rising" | "emerging" | "established";

export type SeasonStatus = "upcoming" | "signing" | "active" | "ended";

export type BadgeType = "first_believer" | "tier_jump";

export type OptOutStatus = "pending" | "approved" | "rejected";

export type VerificationMethod = "email" | "domain" | "manual";

export type JsonValue =
  | string
  | number
  | boolean
  | null
  | { [key: string]: JsonValue }
  | JsonValue[];

export type Profile = {
  id: string;
  display_name: string;
  avatar_url: string | null;
  created_at: string;
  updated_at: string;
};

export type CreateProfile = {
  id: string;
  display_name: string;
  avatar_url: string | null;
};

export type UpdateProfile = Partial<CreateProfile>;

export type Artist = {
  id: string;
  spotify_id: string;
  name: string;
  image_url: string | null;
  genres: string[];
  opted_out: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type CreateArtist = {
  spotify_id: string;
  name: string;
  image_url: string | null;
};

export type UpdateArtist = Partial<CreateArtist>;

export type ListenerSnapshot = {
  id: string;
  artist_id: string;
  monthly_listeners: number;
  captured_at: string;
  created_at: string;
};

export type CreateListenerSnapshot = {
  artist_id: string;
  monthly_listeners: number;
};

export type Season = {
  id: string;
  season_number: number;
  signing_opens_at: string;
  signing_closes_at: string;
  season_ends_at: string;
  status: SeasonStatus;
  artist_pool: string[];
  created_at: string;
  updated_at: string;
};

export type CreateSeason = {
  season_number: number;
  signing_opens_at: string;
  signing_closes_at: string;
  season_ends_at: string;
  status: SeasonStatus;
};

export type UpdateSeason = Partial<CreateSeason>;

export type Roster = {
  id: string;
  user_id: string;
  season_id: string;
  locked_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CreateRoster = {
  user_id: string;
  season_id: string;
  locked_at: string | null;
};

export type UpdateRoster = Partial<CreateRoster>;

export type Signing = {
  id: string;
  roster_id: string;
  artist_id: string;
  slots: number;
  tier_at_signing: Tier;
  listeners_at_signing: number;
  signed_at: string;
  dropped_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CreateSigning = {
  roster_id: string;
  artist_id: string;
  slots: number;
  tier_at_signing: Tier;
  listeners_at_signing: number;
  dropped_at: string | null;
};

export type UpdateSigning = Partial<CreateSigning>;

export type SeasonScore = {
  id: string;
  roster_id: string;
  score: number;
  rank: number;
  computed_at: string;
  created_at: string;
  updated_at: string;
};

export type CreateSeasonScore = {
  roster_id: string;
  score: number;
  rank: number;
};

export type UpdateSeasonScore = Partial<CreateSeasonScore>;

export type Badge = {
  id: string;
  user_id: string;
  artist_id: string;
  season_id: string;
  badge_type: BadgeType;
  earned_at: string;
  created_at: string;
};

export type CreateBadge = {
  user_id: string;
  artist_id: string;
  season_id: string;
  badge_type: BadgeType;
};

export type OptOutRequest = {
  id: string;
  spotify_artist_url: string;
  contact_email: string;
  verification_method: VerificationMethod;
  status: OptOutStatus;
  notes: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CreateOptOutRequest = {
  spotify_artist_url: string;
  contact_email: string;
  verification_method: VerificationMethod;
  notes: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
};

export type UpdateOptOutRequest = Partial<CreateOptOutRequest>;

export type AuditLogEntry = {
  id: string;
  user_id: string | null;
  action: string;
  payload: JsonValue;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
};

export type CreateAuditLogEntry = {
  user_id: string | null;
  action: string;
  ip_address: string | null;
  user_agent: string | null;
};
