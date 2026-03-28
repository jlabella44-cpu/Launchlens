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
