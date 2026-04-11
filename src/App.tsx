import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { ThemeProvider } from "next-themes";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/contexts/AuthContext";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { RequirePermission } from "@/components/auth/RequirePermission";
import { AccessDenied } from "@/components/dashboard/AccessDenied";
import { RequireVerifiedEmail } from "@/components/auth/RequireVerifiedEmail";
import { DashboardNotFound } from "@/components/dashboard/DashboardNotFound";
import { lazy } from "react";

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
const UserDetailPage = lazy(() => import("./pages/admin/UserDetailPage"));
const RoleDetailPage = lazy(() => import("./pages/admin/RoleDetailPage"));

// User pages (lazy loaded)
const UserDashboard = lazy(() => import("./pages/user/UserDashboard"));
const ProfilePage = lazy(() => import("./pages/user/ProfilePage"));
const SecurityPage = lazy(() => import("./pages/user/SecurityPage"));

const queryClient = new QueryClient();

/** Wraps a page with route-level permission enforcement */
function PermissionGate({ permission, children }: { permission: string | string[]; children: React.ReactNode }) {
  return (
    <RequirePermission permission={permission} fallback={<AccessDenied />}>
      {children}
    </RequirePermission>
  );
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <AuthProvider>
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
                  <PermissionGate permission="roles.view">
                    <AdminPermissionsPage />
                  </PermissionGate>
                } />
                <Route path="audit" element={
                  <PermissionGate permission="audit.view">
                    <AdminAuditPage />
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
          </AuthProvider>
        </BrowserRouter>
      </TooltipProvider>
    </ThemeProvider>
  </QueryClientProvider>
);

export default App;
