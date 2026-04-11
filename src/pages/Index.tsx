import { Navigate } from 'react-router-dom';
import { ROUTES } from '@/config/routes';

/**
 * Root route — redirects authenticated users to the dashboard.
 * RequireAuth (in App.tsx) handles unauthenticated → /sign-in redirect.
 */
const Index = () => <Navigate to={ROUTES.DASHBOARD} replace />;

export default Index;
