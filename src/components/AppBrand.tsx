import { cn } from '@/lib/utils';
import logo from '@/assets/marketmuse-logo.png';

interface AppBrandProps {
  appName?: string;
  showName?: boolean;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

const sizeMap = {
  sm: { box: 'h-8 w-8', img: 'h-6 w-6', text: 'text-sm' },
  md: { box: 'h-10 w-10', img: 'h-8 w-8', text: 'text-base' },
  lg: { box: 'h-14 w-14', img: 'h-12 w-12', text: 'text-xl' },
};

export function AppBrand({
  appName = "Beyene'sMarketMuse",
  showName = true,
  className,
  size = 'sm',
}: AppBrandProps) {
  const s = sizeMap[size];
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className={cn('flex shrink-0 items-center justify-center rounded-md bg-primary/10', s.box)}>
        <img
          src={logo}
          alt="Beyene'sMarketMuse logo"
          className={cn('object-contain', s.img)}
          width={512}
          height={512}
          loading="lazy"
        />
      </div>
      {showName && (
        <span className={cn('truncate font-display font-semibold', s.text)}>
          {appName}
        </span>
      )}
    </div>
  );
}
