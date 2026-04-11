import { LucideIcon } from 'lucide-react';

export interface NavItem {
  title: string;
  url: string;
  icon: LucideIcon;
  /** Permission key required to see this item. Omit for always-visible. */
  permission?: string;
  /** Nested items for collapsible groups */
  children?: NavItem[];
  /** Optional badge displayed next to the title (e.g. count or label). Only visible in expanded mode. */
  badge?: string | number;
}

export interface NavSection {
  label: string;
  items: NavItem[];
}
