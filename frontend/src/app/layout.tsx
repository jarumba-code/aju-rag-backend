import React from "react";
import "./globals.css";

export const metadata = {
  title: "Arthur Jarvis University Smart Portal",
  description: "AJU Intelligent RAG Portal for Student Support and Ingestion",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen bg-slate-50 dark:bg-slate-950">
        {children}
      </body>
    </html>
  );
}
