import {
  Radio,
  TrendingUp,
  Zap,
  BarChart2,
  HeartPulse,
  Settings2,
} from 'lucide-react';
import type { NavSection } from './navigation.types';
import { ROUTES } from './routes';

/**
 * Sidebar navigation for the dedicated /trading/* console.
 * Phase 4C — split from admin-navigation so trader users see only
 * trading items, not user-management entries.
 */
export const tradingNavigation: NavSection[] = [
  {
    label: 'Trading',
    items: [
      {
        title: 'War Room',
        url: ROUTES.TRADING_WARROOM,
        icon: Radio,
        permission: 'trading.view',
      },
      {
        title: 'Positions',
        url: ROUTES.TRADING_POSITIONS,
        icon: TrendingUp,
        permission: 'trading.view',
      },
      {
        title: 'Signals',
        url: ROUTES.TRADING_SIGNALS,
        icon: Zap,
        permission: 'trading.view',
      },
      {
        title: 'Performance',
        url: ROUTES.TRADING_PERFORMANCE,
        icon: BarChart2,
        permission: 'trading.view',
      },
      {
        title: 'Engine Health',
        url: ROUTES.TRADING_HEALTH,
        icon: HeartPulse,
        permission: 'trading.view',
      },
      {
        title: 'Config',
        url: ROUTES.TRADING_CONFIG,
        icon: Settings2,
        permission: 'trading.configure',
      },
    ],
  },
];
