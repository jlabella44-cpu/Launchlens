import type { Metadata } from "next";
import "./globals.css";
import { AuthProviderWrapper } from "./auth-wrapper";
import { ErrorBoundary } from "@/components/error-boundary";
import { Footer } from "@/components/layout/footer";
import { OfflineBanner } from "@/components/ui/offline-banner";

export const metadata: Metadata = {
  title: "ListingJet — Put Your Listings on Autopilot",
  description: "AI-powered listing media automation. From raw photos to marketing-ready assets in minutes.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased" suppressHydrationWarning>
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Exo+2:wght@400;500;600;700;800&family=Josefin+Sans:wght@300;400;500;600;700&display=swap"
          rel="stylesheet"
        />
        <script dangerouslySetInnerHTML={{ __html: `
          (function(){try{var t=localStorage.getItem('listingjet_theme');if(t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme:dark)').matches)){document.documentElement.classList.add('dark')}}catch(e){}})();
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
