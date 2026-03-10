import React from 'react';

/**
 * Smallpeice Trust / Arkwright Engineering Scholars brand mark.
 * Approximates the colourful cross/asterisk star shape from the logo.
 */
export default function BrandLogo({ size = 36 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="Arkwright Engineering Scholars"
    >
      {/* Top-left – purple */}
      <path d="M4 4 L18 18 L4 20 Z" fill="#4527a0" opacity="0.9" />
      {/* Top-right – pink */}
      <path d="M36 4 L22 18 L20 4 Z" fill="#e01e8c" opacity="0.9" />
      {/* Bottom-left – navy */}
      <path d="M4 36 L18 22 L20 36 Z" fill="#1d1464" opacity="0.9" />
      {/* Bottom-right – orange */}
      <path d="M36 36 L22 22 L36 20 Z" fill="#f5821e" opacity="0.9" />
      {/* Centre star */}
      <circle cx="20" cy="20" r="4" fill="white" />
    </svg>
  );
}
