import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { ThemeProvider } from "next-themes";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/contexts/AuthContext";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { RequireVerifiedEmail } from "@/components/auth/RequireVerifiedEmail";
import { Suspense, lazy } from "react";
import { LoadingSkeleton } from "@/components/dashboard/LoadingSkeleton";

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

// User pages (lazy loaded)
const UserDashboard = lazy(() => import("./pages/user/UserDashboard"));
const ProfilePage = lazy(() => import("./pages/user/ProfilePage"));
const SecurityPage = lazy(() => import("./pages/user/SecurityPage"));

const queryClient = new QueryClient();

const LazyFallback = () => (
  <div className="p-4 sm:p-6 lg:p-8">
    <LoadingSkeleton variant="page" />
  </div>
);

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

              {/* Admin panel — shared DashboardLayout + admin nav + RequirePermission(admin.access) */}
              <Route path="/admin" element={<AdminLayout />}>
                <Route index element={<Suspense fallback={<LazyFallback />}><AdminDashboard /></Suspense>} />
              </Route>

              {/* User panel — shared DashboardLayout + user nav + RequireAuth */}
              <Route path="/dashboard" element={<UserLayout />}>
                <Route index element={<Suspense fallback={<LazyFallback />}><UserDashboard /></Suspense>} />
              </Route>
              <Route path="/settings" element={<UserLayout />}>
                <Route index element={<Suspense fallback={<LazyFallback />}><ProfilePage /></Suspense>} />
                <Route path="security" element={<Suspense fallback={<LazyFallback />}><SecurityPage /></Suspense>} />
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
