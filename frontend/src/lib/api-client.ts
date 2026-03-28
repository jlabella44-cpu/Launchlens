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

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
      throw new Error(error.detail || `Request failed: ${response.status}`);
    }

    return response.json();
  }

  // Auth
  async register(email: string, password: string, name: string): Promise<TokenResponse> {
    return this.request<TokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, name }),
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
    return this.request<ListingResponse[]>("/listings");
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
}

export const apiClient = new ApiClient();
export default apiClient;
