import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "LabReport AI",
  description: "Educational tool that helps you understand a lab report. It does not diagnose.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="site">
          <strong>LabReport AI</strong>
          <nav>
            <Link href="/">Home</Link>
            <Link href="/login">Log in</Link>
            <Link href="/register">Register</Link>
          </nav>
        </header>
        {children}
        <footer>Educational information only. This tool does not diagnose or give treatment advice.</footer>
      </body>
    </html>
  );
}
