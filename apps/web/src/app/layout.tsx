import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "Trip Companion",
  description: "Plan an editable trip from your dates, stops and preferences.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="site">
          <div>
            <a href="/">Trip Companion</a>
          </div>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
