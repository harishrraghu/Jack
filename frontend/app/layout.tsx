import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BANKNIFTY Analyst",
  description: "Deterministic AI-assisted charting and narrative analyst"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

