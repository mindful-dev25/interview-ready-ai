import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Interview Ready AI",
  description: "Local-LLM interview preparation with agentic RAG and human review.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
