import type { Metadata } from "next";
import { Exo_2, Josefin_Sans } from "next/font/google";
import "./globals.css";
import { AuthProviderWrapper } from "./auth-wrapper";
import { ErrorBoundary } from "@/components/error-boundary";
import { Footer } from "@/components/layout/footer";
import { OfflineBanner } from "@/components/ui/offline-banner";

const exo2 = Exo_2({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-exo2",
  display: "swap",
});

const josefinSans = Josefin_Sans({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-josefin",
  display: "swap",
});

export const metadata: Metadata = {
  title: "ListingJet — Put Your Listings on Autopilot",
  description: "AI-powered listing media automation. From raw photos to marketing-ready assets in minutes.",
  metadataBase: new URL("https://app.listingjet.com"),
  openGraph: {
    title: "ListingJet — Put Your Listings on Autopilot",
    description: "AI-powered listing media automation. From raw photos to marketing-ready assets in minutes.",
    siteName: "ListingJet",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "ListingJet — Put Your Listings on Autopilot",
    description: "AI-powered listing media automation. From raw photos to marketing-ready assets in minutes.",
  },
  icons: {
    icon: "/icon.svg",
    apple: "/icon.svg",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`h-full antialiased ${exo2.variable} ${josefinSans.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: `
          (function(){try{if(!localStorage.getItem('listingjet_theme_v2')){localStorage.removeItem('listingjet_theme');localStorage.setItem('listingjet_theme_v2','1')}var t=localStorage.getItem('listingjet_theme');if(t==='dark'){document.documentElement.classList.add('dark')}}catch(e){}})();
        `}} />
      </head>
      <body className="min-h-full flex flex-col">
        <ErrorBoundary>
          <OfflineBanner />
          <AuthProviderWrapper>
            <div className="flex-1">{children}</div>
            <Footer />
          </AuthProviderWrapper>
        </ErrorBoundary>
      </body>
    </html>
  );
}
