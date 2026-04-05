// NOTE: These types are manually maintained for backwards compatibility.
// The canonical types are generated in ./generated/api.d.ts from the FastAPI OpenAPI spec.
// Run `npm run generate-api` to regenerate. Over time, imports should migrate to ./generated/api.

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
  thumbnail_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface AssetResponse {
  id: string;
  listing_id: string;
  file_path: string;
  file_hash: string;
  state: string;
  thumbnail_url: string | null;
  created_at: string;
}

export interface PackageSelection {
  asset_id: string;
  channel: string;
  position: number;
  composite_score: number;
  selected_by: string;
  thumbnail_url: string | null;
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

export interface DemoCreateResponse {
  demo_id: string;
  upload_urls: Array<{
    index: number;
    key: string;
    upload_url: { url: string; fields: Record<string, string> } | null;
    content_type: string;
  }>;
  expires_at: string;
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

export type BillingStatus = BillingStatusResponse;

export interface BillingStatusResponse {
  plan: string;
  plan_tier: string;
  tier: string;
  billing_model: string;
  credit_balance: number;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
}

export interface CreditBalance {
  balance: number;
  rollover_balance: number;
  rollover_cap: number;
  per_listing_credit_cost: number;
  tier: string;
  period_start: string;
  period_end: string;
}

export interface CreditTransaction {
  id: string;
  amount: number;
  balance_after: number;
  type: string;
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
  id: string;
  size: number;
  credits: number;
  label: string;
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

export interface ReviewAnalytics {
  override_rate: number;
  avg_trust_score: number;
  total_selections: number;
  human_overrides: number;
  total_reviewed: number;
  total_auto_approved: number;
  override_trend: Array<{
    month: string;
    override_rate: number;
    total_selections: number;
    human_overrides: number;
  }>;
}

export interface RejectRequest {
  reason: "quality" | "incomplete" | "non_compliant" | "other";
  detail?: string;
}

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
  plan_tier: string;
  credit_balance: number;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  webhook_url: string | null;
  user_count: number;
  listing_count: number;
  created_at: string;
}

export interface AdminListingItem {
  id: string;
  tenant_id: string;
  tenant_name: string;
  address: Record<string, string>;
  metadata: Record<string, number | string>;
  state: string;
  analysis_tier: string;
  credit_cost: number | null;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
}

export interface AdminUserItem {
  id: string;
  tenant_id: string;
  tenant_name: string;
  email: string;
  name: string | null;
  role: string;
  created_at: string;
}

export interface AuditLogEntry {
  id: string;
  user_id: string;
  tenant_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface SystemEvent {
  id: string;
  tenant_id: string;
  listing_id: string | null;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface RevenueBreakdownResponse {
  subscription_tenant_count: number;
  credit_purchase_count: number;
  total_credits_purchased: number;
  top_tenants_by_usage: { tenant_id: string; credits_used: number }[];
  avg_credits_per_listing: number | null;
}

export interface CreditSummaryResponse {
  total_outstanding: number;
  total_credits_outstanding: number;
  purchased_this_month: number;
  credits_purchased_this_month: number;
  used_this_month: number;
  credits_used_this_month: number;
  expired_this_month: number;
  credits_expired_this_month: number;
  credits_adjusted_this_month: number;
  tenant_count_with_credits: number;
}

export interface TenantCreditsResponse {
  balance: number;
  credit_balance: number;
  transactions: CreditTransactionResponse[];
}

export interface CreditTransactionResponse {
  id: string;
  amount: number;
  balance_after: number;
  transaction_type: string;
  reference_type: string | null;
  reference_id: string | null;
  description: string | null;
  reason: string | null;
  created_at: string;
}

export interface TeamMemberResponse {
  id: string;
  name: string | null;
  email: string;
  role: string;
  created_at: string;
}

export interface InviteTeamMemberRequest {
  email: string;
  name?: string;
  password: string;
  role?: string;
}

export interface ListingPermissionResponse {
  id: string;
  listing_id: string | null;
  grantee_user_id: string;
  grantee_email: string;
  grantee_name: string | null;
  permission: string;
  expires_at: string | null;
  created_at: string;
}

export interface ShareListingRequest {
  email: string;
  permission?: string;
  expires_at?: string | null;
}

export interface AuditLogEntryResponse {
  id: string;
  user_email: string;
  user_name: string | null;
  action: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface SharedListingResponse {
  listing_id: string;
  tenant_id: string;
  address: string;
  state: string;
  permission: string;
  shared_at: string;
  expires_at: string | null;
}

export interface BlanketGrantResponse {
  id: string;
  agent_user_id: string | null;
  agent_name: string | null;
  agent_email: string | null;
  grantee_user_id: string;
  permission: string;
  created_at: string;
}

export interface AnalyticsOverview {
  total_listings: number;
  delivered: number;
  by_state: Record<string, number>;
  avg_pipeline_minutes: number | null;
  success_rate_pct: number | null;
  events_last_30d: Record<string, number>;
}

export interface TimelineDataPoint {
  date: string;
  count: number;
}

export interface AnalyticsTimeline {
  days: number;
  data: TimelineDataPoint[];
}

export interface CreditDataPoint {
  date: string;
  amount: number;
  balance_after: number;
  type: string;
  description: string | null;
}

// Support Tickets

export interface SupportTicket {
  id: string;
  subject: string;
  category: string;
  priority: string;
  status: string;
  created_at: string;
  updated_at: string;
  user_email?: string;
  user_name?: string;
  chat_session_id?: string;
  resolution_note?: string;
}

export interface SupportMessage {
  id: string;
  user_id: string;
  content: string;
  is_admin_reply: boolean;
  created_at: string;
  user_name?: string;
  user_email?: string;
  chat_transcript?: Array<{ role: string; content: string }>;
}

export interface SupportTicketDetail extends SupportTicket {
  messages: SupportMessage[];
}

export interface SupportTicketList {
  items: SupportTicket[];
  total: number;
}

export interface SupportTicketStats {
  open_count: number;
  in_progress_count: number;
  resolved_today: number;
  avg_response_hours: number | null;
}

export interface AnalyticsCredits {
  days: number;
  data: CreditDataPoint[];
}
