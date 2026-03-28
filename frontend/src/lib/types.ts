export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
  name: string;
  role: string;
  tenant_id: string;
}

export interface ListingResponse {
  id: string;
  tenant_id: string;
  address: {
    street?: string;
    city?: string;
    state?: string;
    zip?: string;
  };
  metadata: {
    beds?: number;
    baths?: number;
    sqft?: number;
    price?: number;
  };
  state: string;
  created_at: string;
  updated_at: string;
}

export interface AssetResponse {
  id: string;
  listing_id: string;
  file_path: string;
  file_hash: string;
  state: string;
  created_at: string;
}

export interface PackageSelection {
  asset_id: string;
  channel: string;
  position: number;
  composite_score: number;
  selected_by: string;
}

export interface ExportResponse {
  listing_id: string;
  mode: string;
  download_url: string;
  expires_at: string;
  bundle: {
    photo_count: number | null;
    includes_description: boolean;
    includes_flyer: boolean;
    includes_social_posts: boolean;
  };
}

export interface CreateListingRequest {
  address: Record<string, string>;
  metadata: Record<string, number | string>;
}

export interface CreateAssetsRequest {
  assets: { file_path: string; file_hash: string }[];
}

export interface CreateAssetsResponse {
  count: number;
  listing_state: string;
}

export interface VideoResponse {
  s3_key: string;
  video_type: "ai_generated" | "user_raw" | "professional";
  duration_seconds: number | null;
  status: string;
  chapters: Chapter[] | null;
  social_cuts: SocialCut[] | null;
  thumbnail_s3_key: string | null;
  clip_count: number | null;
  created_at: string;
}

export interface Chapter {
  time: number;
  label: string;
  description: string;
}

export interface SocialCut {
  platform: string;
  s3_key: string;
  width: number;
  height: number;
  max_duration: number;
}

export interface VideoUploadRequest {
  s3_key: string;
  video_type: "user_raw" | "professional";
  duration_seconds?: number;
}

export interface VideoUploadResponse {
  id: string;
  s3_key: string;
  video_type: string;
  status: string;
}

export interface DemoUploadRequest {
  file_paths: string[];
}

export interface DemoUploadResponse {
  demo_id: string;
  photo_count: number;
  expires_at: string;
}

export interface DemoViewResponse {
  demo_id: string;
  address: Record<string, string>;
  state: string;
  is_demo: boolean;
  photos: { file_path: string; room_label?: string; quality_score?: number }[];
}

export interface BillingStatusResponse {
  plan: string;
  plan_tier: string;
  billing_model: string;
  credit_balance: number;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
}

export interface CreditBalance {
  balance: number;
  rollover_balance: number;
  rollover_cap: number;
  period_start: string;
  period_end: string;
}

export interface CreditTransaction {
  id: string;
  amount: number;
  balance_after: number;
  transaction_type: string;
  reference_type: string | null;
  reference_id: string | null;
  description: string | null;
  created_at: string;
}

export interface Addon {
  id: string;
  slug: string;
  name: string;
  credit_cost: number;
  is_active: boolean;
}

export interface CreditBundle {
  size: number;
  price_cents: number;
  per_credit_cents: number;
}

export interface Invoice {
  id: string;
  amount_paid: number;
  currency: string;
  status: string;
  created: number;
  hosted_invoice_url: string | null;
}

export interface UsageResponse {
  listings_this_month: number;
  total_assets: number;
  total_listings: number;
}

export interface PlanLimits {
  max_listings_per_month: number;
  max_assets_per_listing: number;
  tier2_vision: boolean;
  social_content: boolean;
}

export interface BrandKitResponse {
  id: string;
  tenant_id: string;
  logo_url: string | null;
  primary_color: string | null;
  secondary_color: string | null;
  font_primary: string | null;
  agent_name: string | null;
  brokerage_name: string | null;
  raw_config: Record<string, unknown>;
  created_at: string;
}

export interface BrandKitUpsertRequest {
  logo_url?: string | null;
  primary_color?: string | null;
  secondary_color?: string | null;
  font_primary?: string | null;
  agent_name?: string | null;
  brokerage_name?: string | null;
  raw_config?: Record<string, unknown>;
}

export interface PipelineStep {
  name: string;
  status: "pending" | "in_progress" | "completed" | "failed" | "skipped";
  completed_at: string | null;
  progress: string | null;
}

export interface PipelineStatusResponse {
  listing_id: string;
  state: string;
  steps: PipelineStep[];
}

export interface ReviewQueueItem {
  id: string;
  address: Record<string, string>;
  metadata: Record<string, number | string>;
  state: string;
  asset_count: number;
  created_at: string;
}

export interface RejectRequest {
  reason: "quality" | "incomplete" | "non_compliant" | "other";
  detail?: string;
}
