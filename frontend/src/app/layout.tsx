import type { Metadata } from "next";
import "./globals.css";
import { AuthProviderWrapper } from "./auth-wrapper";

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
      <body className="min-h-full flex flex-col">
        <AuthProviderWrapper>{children}</AuthProviderWrapper>
      </body>
    </html>
  );
}
