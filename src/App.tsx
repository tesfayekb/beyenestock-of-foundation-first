import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { ThemeProvider } from "next-themes";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { RequirePermission } from "@/components/auth/RequirePermission";
import { AccessDenied } from "@/components/dashboard/AccessDenied";
import { RequireVerifiedEmail } from "@/components/auth/RequireVerifiedEmail";
import { DashboardNotFound } from "@/components/dashboard/DashboardNotFound";
import { useInactivityTimeout } from "@/hooks/useInactivityTimeout";
import { lazy, useCallback } from "react";

// Public pages (eagerly loaded)
import Index from "./pages/Index";
import NotFound from "./pages/NotFound";
import SignIn from "./pages/SignIn";
import SignUp from "./pages/SignUp";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import MfaChallenge from "./pages/MfaChallenge";
import MfaEnroll from "./pages/MfaEnroll";

// Layouts (eagerly loaded — shell must be ready immediately)
import { AdminLayout } from "./layouts/AdminLayout";
import { UserLayout } from "./layouts/UserLayout";

// Admin pages (lazy loaded)
const AdminDashboard = lazy(() => import("./pages/admin/AdminDashboard"));
const AdminUsersPage = lazy(() => import("./pages/admin/AdminUsersPage"));
const AdminRolesPage = lazy(() => import("./pages/admin/AdminRolesPage"));
const AdminPermissionsPage = lazy(() => import("./pages/admin/AdminPermissionsPage"));
const AdminAuditPage = lazy(() => import("./pages/admin/AdminAuditPage"));
const AdminHealthPage = lazy(() => import("./pages/admin/AdminHealthPage"));
const AdminJobsPage = lazy(() => import("./pages/admin/AdminJobsPage"));
const AdminOnboardingPage = lazy(() => import("./pages/admin/AdminOnboardingPage"));
const UserDetailPage = lazy(() => import("./pages/admin/UserDetailPage"));
const RoleDetailPage = lazy(() => import("./pages/admin/RoleDetailPage"));
const TradingHealthPage = lazy(() => import("./pages/admin/trading/HealthPage"));

// User pages (lazy loaded)
const UserDashboard = lazy(() => import("./pages/user/UserDashboard"));
const ProfilePage = lazy(() => import("./pages/user/ProfilePage"));
const SecurityPage = lazy(() => import("./pages/user/SecurityPage"));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 2 * 60 * 1000, // 2 minutes — admin data changes infrequently
      gcTime: 10 * 60 * 1000,   // 10 minutes — keep cache across navigation
      retry: 2,
      retryDelay: (attemptIndex) => Math.min(500 * 2 ** attemptIndex, 5000),
    },
  },
});

/** Wraps a page with route-level permission enforcement */
function PermissionGate({ permission, children }: { permission: string | string[]; children: React.ReactNode }) {
  return (
    <RequirePermission permission={permission} fallback={<AccessDenied />}>
      {children}
    </RequirePermission>
  );
}

/** Inactivity timeout wrapper — must be inside BrowserRouter + AuthProvider */
function InactivityGuard({ children }: { children: React.ReactNode }) {
  const { user, signOut } = useAuth();
  const handleTimeout = useCallback(async () => {
    await signOut();
  }, [signOut]);

  useInactivityTimeout({
    onTimeout: handleTimeout,
    enabled: !!user,
  });

  return <>{children}</>;
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <AuthProvider>
            <InactivityGuard>
            <Routes>
              {/* Public auth routes */}
              <Route path="/sign-in" element={<SignIn />} />
              <Route path="/sign-up" element={<SignUp />} />
              <Route path="/forgot-password" element={<ForgotPassword />} />
              <Route path="/reset-password" element={<ResetPassword />} />
              <Route path="/mfa-challenge" element={<MfaChallenge />} />

              {/* Protected — require auth + verified email */}
              <Route path="/" element={
                <RequireAuth>
                  <RequireVerifiedEmail>
                    <Index />
                  </RequireVerifiedEmail>
                </RequireAuth>
              } />
              <Route path="/mfa-enroll" element={
                <RequireAuth>
                  <RequireVerifiedEmail>
                    <MfaEnroll />
                  </RequireVerifiedEmail>
                </RequireAuth>
              } />

              {/* Admin panel — AdminLayout enforces admin.access, individual routes add granular permissions */}
              <Route path="/admin" element={<AdminLayout />}>
                <Route index element={<AdminDashboard />} />
                <Route path="users" element={
                  <PermissionGate permission="users.view_all">
                    <AdminUsersPage />
                  </PermissionGate>
                } />
                <Route path="users/:id" element={
                  <PermissionGate permission="users.view_all">
                    <UserDetailPage />
                  </PermissionGate>
                } />
                <Route path="roles" element={
                  <PermissionGate permission="roles.view">
                    <AdminRolesPage />
                  </PermissionGate>
                } />
                <Route path="roles/:id" element={
                  <PermissionGate permission="roles.view">
                    <RoleDetailPage />
                  </PermissionGate>
                } />
                <Route path="permissions" element={
                  <PermissionGate permission="permissions.view">
                    <AdminPermissionsPage />
                  </PermissionGate>
                } />
                <Route path="audit" element={
                  <PermissionGate permission="audit.view">
                    <AdminAuditPage />
                  </PermissionGate>
                } />
                <Route path="health" element={
                  <PermissionGate permission="monitoring.view">
                    <AdminHealthPage />
                  </PermissionGate>
                } />
                <Route path="jobs" element={
                  <PermissionGate permission="jobs.view">
                    <AdminJobsPage />
                  </PermissionGate>
                } />
                <Route path="onboarding" element={
                  <PermissionGate permission="users.invite">
                    <AdminOnboardingPage />
                  </PermissionGate>
                } />
                <Route path="trading/health" element={
                  <PermissionGate permission="trading.view">
                    <TradingHealthPage />
                  </PermissionGate>
                } />
                <Route path="*" element={<DashboardNotFound />} />
              </Route>

              {/* User panel */}
              <Route path="/dashboard" element={<UserLayout />}>
                <Route index element={<UserDashboard />} />
                <Route path="*" element={<DashboardNotFound />} />
              </Route>
              <Route path="/settings" element={<UserLayout />}>
                <Route index element={
                  <PermissionGate permission="profile.self_manage">
                    <ProfilePage />
                  </PermissionGate>
                } />
                <Route path="security" element={
                  <PermissionGate permission="mfa.self_manage">
                    <SecurityPage />
                  </PermissionGate>
                } />
                <Route path="*" element={<DashboardNotFound />} />
              </Route>

              {/* Catch-all */}
              <Route path="*" element={<NotFound />} />
            </Routes>
            </InactivityGuard>
          </AuthProvider>
        </BrowserRouter>
      </TooltipProvider>
    </ThemeProvider>
  </QueryClientProvider>
);

export default App;
