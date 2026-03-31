import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Backend API base URL — single source of truth for all fetch calls. */
export const API_BASE = import.meta.env.VITE_API_URL || "https://vizifi.onrender.com";
