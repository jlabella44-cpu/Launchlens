import type { Metadata } from "next";
import "./globals.css";
import { AuthProviderWrapper } from "./auth-wrapper";
import { ClientProviders } from "./client-providers";

export const metadata: Metadata = {
  title: "LaunchLens — Listing Media OS",
  description: "From raw listing media to launch-ready marketing in minutes.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;500;600;700&family=Josefin+Sans:wght@300;400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-full flex flex-col">
        <ClientProviders>
          <AuthProviderWrapper>{children}</AuthProviderWrapper>
        </ClientProviders>
      </body>
    </html>
  );
}
