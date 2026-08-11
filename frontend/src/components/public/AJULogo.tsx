"use client";

import React from "react";

interface AJULogoProps {
  className?: string;
  size?: "sm" | "md" | "lg";
  showText?: boolean;
}

const sizeClasses = {
  sm: "h-8",
  md: "h-12",
  lg: "h-16",
};

export default function AJULogo({ className = "", size = "md", showText = true }: AJULogoProps) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {/* Official AJU Logo SVG */}
      <svg
        viewBox="0 0 320 100"
        className={`${sizeClasses[size]} w-auto flex-shrink-0`}
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-label="Arthur Jarvis University"
      >
        {/* Graduation cap silhouette */}
        <g transform="translate(8, 18)">
          <path
            d="M12 0L24 8L12 16L0 8L12 0Z"
            fill="#0a1628"
          />
          <path
            d="M12 16L24 8V16L12 24L0 16V8L12 16Z"
            fill="#0a1628"
          />
          <rect x="10" y="24" width="4" height="12" fill="#0a1628" />
          <circle cx="12" cy="38" r="3" fill="#0a1628" />
        </g>

        {/* Wing flourish */}
        <g transform="translate(28, 10)" stroke="#d4af37" strokeWidth="2.5" fill="none" strokeLinecap="round">
          <path d="M0 20 Q15 0 40 10" />
          <path d="M5 25 Q18 8 45 14" />
          <path d="M10 30 Q22 15 50 18" />
        </g>

        {/* University name */}
        <text x="80" y="38" fontFamily="Georgia, Cambria, serif" fontSize="22" fontWeight="bold" fill="#0a1628">
          ARTHUR JARVIS
        </text>
        <text x="80" y="62" fontFamily="Georgia, Cambria, serif" fontSize="22" fontWeight="bold" fill="#0a1628">
          UNIVERSITY
        </text>

        {/* Gold underline accent */}
        <rect x="80" y="68" width="180" height="3" fill="#d4af37" rx="1.5" />

        {/* Motto */}
        <text x="80" y="86" fontFamily="Georgia, Cambria, serif" fontSize="11" fontStyle="italic" fill="#b8962e">
          Onion ye Ifiok
        </text>
      </svg>
    </div>
  );
}
