import type { Metadata } from "next";
import { IBM_Plex_Mono, Manrope } from "next/font/google";

import { AppShellProvider } from "@/providers/app-shell-provider";

import "./globals.css";

const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-manrope"
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono"
});

export const metadata: Metadata = {
  title: "AML Check Enterprise",
  description: "Professional AML / KYC / Compliance screening platform"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt" className="dark">
      <body className={`${manrope.variable} ${mono.variable}`}>
        <AppShellProvider>{children}</AppShellProvider>
      </body>
    </html>
  );
}
