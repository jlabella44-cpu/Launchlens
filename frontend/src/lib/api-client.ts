import type {
  TokenResponse,
  UserResponse,
  ListingResponse,
  AssetResponse,
  PackageSelection,
  ExportResponse,
  CreateListingRequest,
  CreateAssetsRequest,
  CreateAssetsResponse,
  AdminStatsResponse,
  AdminTenantResponse,
  CreditSummaryResponse,
  TenantCreditsResponse,
  CreditBalance,
  CreditTransaction,
  CreditBundle,
  Addon,
  VideoResponse,
  SocialCut,
  VideoUploadRequest,
  VideoUploadResponse,
  DemoUploadRequest,
  DemoUploadResponse,
  DemoViewResponse,
  BillingStatusResponse,
  Invoice,
  UsageResponse,
  BrandKitResponse,
  BrandKitUpsertRequest,
  PipelineStatusResponse,
  ReviewQueueItem,
  RejectRequest,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://Listin-ApiSe-Ly4m06X1ArNQ-22089779.us-east-1.elb.amazonaws.com";

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
  }

  getToken(): string | null {
    return this.token;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "ngrok-skip-browser-warning": "true",
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      const err = new Error(error.detail || `Request failed: ${response.status}`) as Error & { status: number };
      err.status = response.status;
      throw err;
    }

    return response.json();
  }

  // Auth
  async register(
    email: string,
    password: string,
    name: string,
    companyName: string,
    planTier?: string,
  ): Promise<TokenResponse> {
    return this.request<TokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
        name,
        company_name: companyName,
        plan_tier: planTier || undefined,
      }),
    });
  }

  async login(email: string, password: string): Promise<TokenResponse> {
    return this.request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  }

  async me(): Promise<UserResponse> {
    return this.request<UserResponse>("/auth/me");
  }

  // Listings
  async createListing(data: CreateListingRequest): Promise<ListingResponse> {
    return this.request<ListingResponse>("/listings", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getListings(): Promise<ListingResponse[]> {
    const res = await this.request<{ items: ListingResponse[] } | ListingResponse[]>("/listings");
    return Array.isArray(res) ? res : res.items;
  }

  async getListing(id: string): Promise<ListingResponse> {
    return this.request<ListingResponse>(`/listings/${id}`);
  }

  // Assets
  async registerAssets(listingId: string, data: CreateAssetsRequest): Promise<CreateAssetsResponse> {
    return this.request<CreateAssetsResponse>(`/listings/${listingId}/assets`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getAssets(listingId: string): Promise<AssetResponse[]> {
    return this.request<AssetResponse[]>(`/listings/${listingId}/assets`);
  }

  // Package
  async getPackage(listingId: string): Promise<PackageSelection[]> {
    return this.request<PackageSelection[]>(`/listings/${listingId}/package`);
  }

  // Review flow
  async startReview(listingId: string): Promise<{ listing_id: string; state: string }> {
    return this.request(`/listings/${listingId}/review`, { method: "POST" });
  }

  async retryPipeline(listingId: string): Promise<{ listing_id: string; state: string }> {
    return this.request(`/listings/${listingId}/retry`, { method: "POST" });
  }

  async approveListing(listingId: string): Promise<{ listing_id: string; state: string }> {
    return this.request(`/listings/${listingId}/approve`, { method: "POST" });
  }

  // Export
  async getExport(listingId: string, mode: "mls" | "marketing" = "marketing"): Promise<ExportResponse> {
    return this.request<ExportResponse>(`/listings/${listingId}/export?mode=${mode}`);
  }

  // Video
  async getVideo(listingId: string): Promise<VideoResponse> {
    return this.request<VideoResponse>(`/listings/${listingId}/video`);
  }

  async getSocialCuts(listingId: string): Promise<SocialCut[]> {
    return this.request<SocialCut[]>(`/listings/${listingId}/video/social-cuts`);
  }

  async uploadVideo(listingId: string, data: VideoUploadRequest): Promise<VideoUploadResponse> {
    return this.request<VideoUploadResponse>(`/listings/${listingId}/video/upload`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // Retry failed listing
  async retryListing(listingId: string): Promise<{ listing_id: string; state: string }> {
    return this.request(`/listings/${listingId}/retry`, { method: "POST" });
  }

  // Demo (no auth required)
  async demoUpload(data: DemoUploadRequest): Promise<DemoUploadResponse> {
    return this.request<DemoUploadResponse>("/demo/upload", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async demoView(id: string): Promise<DemoViewResponse> {
    return this.request<DemoViewResponse>(`/demo/${id}`);
  }

  async demoClaim(id: string): Promise<{ listing_id: string }> {
    return this.request<{ listing_id: string }>(`/demo/${id}/claim`, { method: "POST" });
  }

  // Billing
  async billingStatus(): Promise<BillingStatusResponse> {
    return this.request<BillingStatusResponse>("/billing/status");
  }

  async billingCheckout(priceId: string, successUrl: string, cancelUrl: string): Promise<{ checkout_url: string }> {
    return this.request<{ checkout_url: string }>("/billing/checkout", {
      method: "POST",
      body: JSON.stringify({ price_id: priceId, success_url: successUrl, cancel_url: cancelUrl }),
    });
  }

  async billingPortal(returnUrl: string): Promise<{ portal_url: string }> {
    return this.request<{ portal_url: string }>("/billing/portal", {
      method: "POST",
      body: JSON.stringify({ return_url: returnUrl }),
    });
  }

  async billingInvoices(limit = 10): Promise<{ invoices: Invoice[] }> {
    return this.request<{ invoices: Invoice[] }>(`/billing/invoices?limit=${limit}`);
  }

  // Usage (analytics)
  async getUsage(): Promise<UsageResponse> {
    return this.request<UsageResponse>("/analytics/usage");
  }

  // Brand Kit
  async getBrandKit(): Promise<BrandKitResponse | null> {
    return this.request<BrandKitResponse | null>("/brand-kit");
  }

  async upsertBrandKit(data: BrandKitUpsertRequest): Promise<BrandKitResponse> {
    return this.request<BrandKitResponse>("/brand-kit", {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async getLogoUploadUrl(): Promise<{ key: string; upload: Record<string, unknown> }> {
    return this.request("/brand-kit/logo-upload-url", { method: "POST" });
  }

  // Upload URLs
  async getUploadUrls(listingId: string, filenames: string[]): Promise<{
    urls: { filename: string; key: string; upload_url: string; content_type: string }[];
  }> {
    return this.request(`/listings/${listingId}/upload-urls`, {
      method: "POST",
      body: JSON.stringify({ filenames }),
    });
  }

  // Pipeline status
  async getPipelineStatus(listingId: string): Promise<PipelineStatusResponse> {
    return this.request<PipelineStatusResponse>(`/listings/${listingId}/pipeline-status`);
  }

  // Review queue
  async getReviewQueue(): Promise<ListingResponse[]> {
    return this.request<ListingResponse[]>("/listings?state=awaiting_review");
  }

  // Reject
  async rejectListing(listingId: string, data: RejectRequest): Promise<{ listing_id: string; state: string }> {
    return this.request(`/listings/${listingId}/reject`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async cancelListing(listingId: string): Promise<{ listing_id: string; state: string; credits_refunded: number }> {
    return this.request(`/listings/${listingId}/cancel`, { method: "POST" });
  }

  // Credits
  async getCreditBalance(): Promise<CreditBalance> {
    return this.request<CreditBalance>("/credits/balance");
  }

  async getCreditTransactions(limit = 50, offset = 0): Promise<CreditTransaction[]> {
    return this.request<CreditTransaction[]>(`/credits/transactions?limit=${limit}&offset=${offset}`);
  }

  async getCreditPricing(): Promise<{ bundles: CreditBundle[] }> {
    return this.request("/credits/pricing");
  }

  async getCreditBundles(): Promise<CreditBundle[]> {
    const data = await this.getCreditPricing();
    return data.bundles;
  }

  async purchaseCredits(bundleSize: number, successUrl: string, cancelUrl: string): Promise<{ checkout_url: string }> {
    return this.request("/credits/purchase", {
      method: "POST",
      body: JSON.stringify({ bundle_size: bundleSize, success_url: successUrl, cancel_url: cancelUrl }),
    });
  }

  // Addons
  async getAddons(): Promise<Addon[]> {
    return this.request<Addon[]>("/addons");
  }

  async activateAddon(listingId: string, addonSlug: string): Promise<{ id: string; addon_slug: string; status: string }> {
    return this.request(`/listings/${listingId}/addons`, {
      method: "POST",
      body: JSON.stringify({ addon_slug: addonSlug }),
    });
  }

  async getListingAddons(listingId: string): Promise<{ addon_slug: string; addon_name: string; status: string }[]> {
    return this.request(`/listings/${listingId}/addons`);
  }

  async removeAddon(listingId: string, addonSlug: string): Promise<{ status: string; credits_returned: number }> {
    return this.request(`/listings/${listingId}/addons/${addonSlug}`, { method: "DELETE" });
  }

  // Admin
  async adminStats(): Promise<AdminStatsResponse> {
    return this.request<AdminStatsResponse>("/admin/stats");
  }

  async adminTenants(): Promise<AdminTenantResponse[]> {
    return this.request<AdminTenantResponse[]>("/admin/tenants");
  }

  async adminCreditsSummary(): Promise<CreditSummaryResponse> {
    return this.request<CreditSummaryResponse>("/admin/credits/summary");
  }

  async adminTenantCredits(tenantId: string): Promise<TenantCreditsResponse> {
    return this.request<TenantCreditsResponse>(`/admin/tenants/${tenantId}/credits`);
  }

  async adminAdjustCredits(tenantId: string, amount: number, reason: string): Promise<void> {
    await this.request(`/admin/tenants/${tenantId}/credits/adjust`, {
      method: "POST",
      body: JSON.stringify({ amount, reason }),
    });
  }
}

export const apiClient = new ApiClient();
export default apiClient;
