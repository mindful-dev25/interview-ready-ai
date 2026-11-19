import type { Metadata } from "next";
import PasswordGate from "@/components/PasswordGate";
import "./globals.css";

export const metadata: Metadata = {
  title: "Interview Ready AI",
  description: "Claude-backed interview preparation with agentic RAG and human review.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <PasswordGate>{children}</PasswordGate>
      </body>
    </html>
  );
}
