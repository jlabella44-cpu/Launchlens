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
}

export const apiClient = new ApiClient();
export default apiClient;
