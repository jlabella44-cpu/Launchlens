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
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
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

// Admin types
export interface AdminStatsResponse {
  total_tenants: number;
  total_users: number;
  total_listings: number;
  listings_by_state: Record<string, number>;
}

export interface AdminTenantResponse {
  id: string;
  name: string;
  plan: string;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  webhook_url: string | null;
  credit_balance?: number;
  created_at: string;
}

export interface CreditTransactionResponse {
  id: string;
  tenant_id: string;
  amount: number;
  balance_after: number;
  transaction_type: string;
  reason: string | null;
  created_at: string;
}

export interface TenantCreditsResponse {
  tenant_id: string;
  credit_balance: number;
  transactions: CreditTransactionResponse[];
}

export interface CreditSummaryResponse {
  total_credits_outstanding: number;
  credits_purchased_this_month: number;
  credits_used_this_month: number;
  credits_adjusted_this_month: number;
  tenant_count_with_credits: number;
}

export interface RevenueBreakdownResponse {
  subscription_tenant_count: number;
  credit_purchase_count: number;
  total_credits_purchased: number;
  top_tenants_by_usage: { tenant_id: string; name: string; credits_used: number }[];
  avg_credits_per_listing: number | null;
}
