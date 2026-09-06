import type { NextConfig } from "next";

// Public hostname of the media bucket (Cloudflare R2 public bucket domain or a
// custom domain in front of it), e.g. "media.listingjet.ai" or
// "pub-xxxx.r2.dev". Set per environment; without it next/image rejects every
// listing photo.
const mediaHost = process.env.NEXT_PUBLIC_MEDIA_HOST;

if (process.env.NODE_ENV === "production" && !mediaHost) {
  throw new Error("NEXT_PUBLIC_MEDIA_HOST is required for production builds");
}

const nextConfig: NextConfig = {
  images: {
    formats: ["image/webp"],
    remotePatterns: mediaHost
      ? [{ protocol: "https", hostname: mediaHost }]
      : [],
  },
};

export default nextConfig;
