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

// Credit system types

export interface CreditBalance {
  balance: number;
  billing_model: "legacy" | "credit";
  tier: string;
  per_listing_credit_cost: number;
  rollover_cap: number | null;
}

export interface CreditTransaction {
  id: string;
  amount: number;
  type: "purchase" | "usage" | "refund" | "rollover" | "bonus";
  description: string;
  listing_id: string | null;
  created_at: string;
}

export interface CreditBundle {
  id: string;
  credits: number;
  price_cents: number;
  label: string;
}

export interface CreditCheckoutResponse {
  checkout_url: string;
}

export interface Addon {
  id: string;
  addon_type: "ai_video_tour" | "3d_floorplan" | "social_pack";
  credit_cost: number;
  status: "active" | "cancelled";
  listing_id: string;
  created_at: string;
}

export interface BillingStatus {
  billing_model: "legacy" | "credit";
  plan: string;
  tier: string;
  stripe_customer_id: string | null;
}
