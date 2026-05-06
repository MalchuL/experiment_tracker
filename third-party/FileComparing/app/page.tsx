'use client';

import { FileCompareView } from '@/components/file-compare-view';

// Example files for the left side (Version A)
const leftFiles = [
  {
    path: '/src/components/Button.tsx',
    content: `import React from 'react';

interface ButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary';
}

export function Button({ children, onClick, variant = 'primary' }: ButtonProps) {
  return (
    <button
      onClick={onClick}
      className={\`btn btn-\${variant}\`}
    >
      {children}
    </button>
  );
}`,
  },
  {
    path: '/src/components/Card.tsx',
    content: `import React from 'react';

interface CardProps {
  title: string;
  children: React.ReactNode;
}

export function Card({ title, children }: CardProps) {
  return (
    <div className="card">
      <h2>{title}</h2>
      <div className="card-content">
        {children}
      </div>
    </div>
  );
}`,
  },
  {
    path: '/src/utils/helpers.ts',
    content: `export function formatDate(date: Date): string {
  return date.toLocaleDateString();
}

export function capitalizeFirst(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1);
}`,
  },
  {
    path: '/src/config/constants.ts',
    content: `export const API_URL = 'https://api.example.com';
export const APP_NAME = 'My App';
export const VERSION = '1.0.0';`,
  },
  {
    path: '/src/styles/theme.css',
    content: `:root {
  --primary-color: #007bff;
  --secondary-color: #6c757d;
  --background: #ffffff;
  --text-color: #212529;
}`,
  },
];

// Example files for the right side (Version B)
const rightFiles = [
  {
    path: '/src/components/Button.tsx',
    content: `import React from 'react';
import { cn } from '@/lib/utils';

interface ButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary' | 'outline';
  disabled?: boolean;
}

export function Button({ 
  children, 
  onClick, 
  variant = 'primary',
  disabled = false 
}: ButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'btn',
        \`btn-\${variant}\`,
        disabled && 'btn-disabled'
      )}
    >
      {children}
    </button>
  );
}`,
  },
  {
    path: '/src/components/Card.tsx',
    content: `import React from 'react';

interface CardProps {
  title: string;
  description?: string;
  children: React.ReactNode;
}

export function Card({ title, description, children }: CardProps) {
  return (
    <div className="card">
      <div className="card-header">
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>
      <div className="card-content">
        {children}
      </div>
    </div>
  );
}`,
  },
  {
    path: '/src/utils/helpers.ts',
    content: `export function formatDate(date: Date, locale: string = 'en-US'): string {
  return date.toLocaleDateString(locale);
}

export function capitalizeFirst(str: string): string {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1);
}

export function formatCurrency(amount: number, currency: string = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
  }).format(amount);
}`,
  },
  {
    path: '/src/config/constants.ts',
    content: `export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.example.com';
export const APP_NAME = 'My App';
export const VERSION = '2.0.0';
export const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB`,
  },
  {
    path: '/src/styles/theme.css',
    content: `:root {
  --primary-color: #0070f3;
  --secondary-color: #6c757d;
  --background: #ffffff;
  --foreground: #000000;
  --text-color: #212529;
  --border-radius: 8px;
}`,
  },
  {
    path: '/src/lib/utils.ts',
    content: `import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}`,
  },
];

export default function Page() {
  return (
    <FileCompareView
      leftFiles={leftFiles}
      rightFiles={rightFiles}
      leftLabel="Version 1.0"
      rightLabel="Version 2.0"
    />
  );
}
