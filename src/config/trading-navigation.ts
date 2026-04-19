import {
  Radio,
  TrendingUp,
  Zap,
  BarChart2,
  HeartPulse,
  Settings2,
  Brain,
  Flag,
  BookOpen,
  Target,
  CreditCard,
  Layers,
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
  {
    label: 'Intelligence',
    items: [
      {
        title: 'AI Intelligence',
        url: ROUTES.TRADING_INTELLIGENCE,
        icon: Brain,
        permission: 'trading.view',
      },
      {
        title: 'Feature Flags',
        url: ROUTES.TRADING_FLAGS,
        icon: Flag,
        permission: 'trading.configure',
      },
    ],
  },
  {
    label: 'System',
    items: [
      {
        title: 'Strategy Library',
        url: ROUTES.TRADING_STRATEGIES,
        icon: BookOpen,
        permission: 'trading.view',
      },
      {
        title: 'Milestones',
        url: ROUTES.TRADING_MILESTONES,
        icon: Target,
        permission: 'trading.view',
      },
      {
        title: 'Activation',
        url: ROUTES.TRADING_ACTIVATION,
        icon: Layers,
        permission: 'trading.configure',
      },
      {
        title: 'Subscriptions',
        url: ROUTES.TRADING_SUBSCRIPTIONS,
        icon: CreditCard,
        permission: 'trading.configure',
      },
    ],
  },
];
