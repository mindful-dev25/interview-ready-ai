import type { Metadata } from "next";
import SignInGate from "@/components/SignInGate";
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
        <SignInGate>{children}</SignInGate>
      </body>
    </html>
  );
}
