/*
Purpose:
Premium enterprise login page with modern branding and animations.
*/

import { FormEvent, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, Cloud, LockKeyhole, Database, Shield, Zap, ChevronRight } from "lucide-react";
import { Navigate, useLocation, useNavigate, Link } from "react-router-dom";

import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { authService } from "@/services/authService";
import { env } from "@/lib/env";

interface LocationState {
  from?: {
    pathname?: string;
  };
}

// Floating particle component
function FloatingParticle({ delay, duration, size }: { delay: number; duration: number; size: number }) {
  const { startX, xDrift } = useMemo(
    () => ({
      startX: Math.random() * (typeof window !== "undefined" ? window.innerWidth : 1000),
      xDrift: Math.random() * 100 - 50,
    }),
    [],
  );

  return (
    <motion.div
      className="absolute rounded-full bg-primary/20 blur-sm"
      style={{ width: size, height: size }}
      initial={{ x: startX, y: typeof window !== "undefined" ? window.innerHeight + 100 : 800, opacity: 0 }}
      animate={{ y: -100, opacity: [0, 0.6, 0], x: [0, xDrift] }}
      transition={{ duration, delay, repeat: Infinity, repeatType: "loop" }}
    />
  );
}

export function LoginPage() {
  const { isAuthenticated, isLoading, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const locationState = location.state as LocationState | null;
  const redirectTo = locationState?.from?.pathname || "/dashboard";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background text-foreground">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex flex-col items-center gap-4"
        >
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            className="relative"
          >
            <div className="absolute inset-0 rounded-full bg-primary/20 blur-xl" />
            <Cloud className="h-12 w-12 text-primary relative z-10" />
          </motion.div>
          <p className="text-sm font-medium tracking-wide text-muted-foreground">Initializing secure session...</p>
        </motion.div>
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  const handleGoogleLogin = async () => {
    setError(null);
    setIsSubmitting(true);

    try {
      if (!env.cognitoClientId) {
        throw new Error("Google OAuth is not configured. Set VITE_COGNITO_CLIENT_ID in your environment.");
      }

      // Use the Google Identity Services library if available
      const google = (window as any).google;
      if (google?.accounts?.id) {
        const credential = await new Promise<string>((resolve, reject) => {
          google.accounts.id.initialize({
            client_id: env.cognitoClientId,
            callback: (response: any) => resolve(response.credential),
            onerror: () => reject(new Error("Google sign-in was cancelled or failed.")),
          });
          google.accounts.id.prompt();
        });

        const response = await authService.googleOAuthLogin({ id_token: credential });
        console.log("Google OAuth login successful:", response);
      } else {
        throw new Error("Google OAuth is not available. Ensure the Google Identity Services script is loaded.");
      }
      navigate(redirectTo, { replace: true });
    } catch (loginError) {
      console.error("Google OAuth login error:", loginError);
      if (loginError instanceof Error) {
        if (loginError.message.includes("Network Error") || loginError.message.includes("fetch")) {
          setError(`Unable to connect to the server. Please ensure the backend is running at ${env.apiBaseUrl}`);
        } else {
          setError(loginError.message);
        }
      } else {
        setError("Google authentication failed. Please try again or use email/password login.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await login({ email, password });
      navigate(redirectTo, { replace: true });
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : "Authentication failed. Please check your credentials.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const features = [
    { icon: Database, title: "CDC Replication", description: "Real-time change data capture", gradient: "from-blue-500 to-cyan-400" },
    { icon: Shield, title: "Schema Drift Detection", description: "Automated monitoring & alerts", gradient: "from-violet-500 to-purple-400" },
    { icon: Zap, title: "ECS Execution", description: "Scalable migration workers", gradient: "from-amber-500 to-orange-400" },
  ];

  return (
    <main className="min-h-screen bg-gradient-to-br from-background via-background to-background text-foreground relative overflow-hidden dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 dark:text-white">
      {/* Animated gradient background */}
      <div className="absolute inset-0">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary/20 rounded-full blur-[128px] animate-pulse" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-[128px] animate-pulse" style={{ animationDelay: "1s" }} />
        <div className="absolute top-1/2 left-1/2 w-64 h-64 bg-purple-500/10 rounded-full blur-[96px] animate-pulse" style={{ animationDelay: "2s" }} />
      </div>

      {/* Floating particles */}
      {Array.from({ length: 20 }).map((_, i) => (
        <FloatingParticle key={i} delay={i * 0.5} duration={15 + Math.random() * 10} size={4 + Math.random() * 8} />
      ))}

      {/* Grid pattern overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(128,128,128,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(128,128,128,0.05)_1px,transparent_1px)] bg-[size:64px_64px] dark:bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)]" />

      <div className="absolute right-6 top-6 z-50">
        <ThemeToggle />
      </div>

      <div className="relative z-10 min-h-screen flex items-center justify-center p-6">
        <div className="w-full max-w-7xl grid lg:grid-cols-2 gap-16 items-center">
          {/* Left Panel - Branding */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6 }}
            className="hidden lg:block"
          >
            <div className="space-y-8">
              {/* Logo */}
              <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="flex items-center gap-4"
              >
                <div className="relative">
                  <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-primary to-blue-500 blur-lg opacity-50" />
                  <div className="relative grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-primary to-blue-500 text-white shadow-2xl">
                    <Cloud className="h-7 w-7" />
                  </div>
                </div>
                <div>
                  <h1 className="text-3xl font-bold tracking-tight">CloudBridge</h1>
                  <p className="text-sm text-muted-foreground font-medium">Enterprise Migration Platform</p>
                </div>
              </motion.div>

              {/* Hero text */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="space-y-4"
              >
                <h2 className="text-5xl font-bold leading-tight bg-gradient-to-r from-foreground via-foreground to-foreground/70 bg-clip-text text-transparent dark:from-white dark:via-white dark:to-white/70">
                  Migrate databases at scale
                </h2>
                <p className="text-xl text-muted-foreground leading-relaxed max-w-lg">
                  Enterprise-grade database migration platform with CDC, schema drift detection, and automated rollback capabilities.
                </p>
              </motion.div>

              {/* Feature cards */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="space-y-4"
              >
                {features.map((feature, index) => (
                  <motion.div
                    key={feature.title}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.5 + index * 0.1 }}
                    className="flex items-start gap-4 p-4 rounded-2xl border border-border/10 bg-background/50 backdrop-blur-sm hover:bg-muted/50 transition-colors group dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10"
                  >
                    <div className={`h-10 w-10 rounded-xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center text-white shadow-md group-hover:scale-110 transition-all duration-300`}>
                      <feature.icon className="h-5 w-5" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-foreground dark:text-white">{feature.title}</h3>
                      <p className="text-sm text-muted-foreground">{feature.description}</p>
                    </div>
                  </motion.div>
                ))}
              </motion.div>
            </div>
          </motion.div>

          {/* Right Panel - Login Form */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6 }}
            className="flex justify-center"
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2, duration: 0.4 }}
              className="w-full max-w-md"
            >
              <Card className="border border-border/10 bg-card/50 backdrop-blur-xl shadow-2xl relative overflow-hidden dark:border-white/10 dark:bg-white/[0.02]">
                {/* Animated gradient border */}
                <div className="absolute inset-0 bg-gradient-to-br from-primary/20 via-transparent to-blue-500/20 opacity-0 hover:opacity-100 transition-opacity duration-500" />
                
                <div className="relative">
                  <CardHeader className="space-y-3 pb-6">
                    <motion.div
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: 0.3 }}
                      className="flex justify-center mb-4"
                    >
                      <div className="relative">
                        <div className="absolute inset-0 rounded-2xl bg-primary/30 blur-xl" />
                        <div className="relative grid h-16 w-16 place-items-center rounded-2xl bg-gradient-to-br from-primary to-blue-500 text-white shadow-2xl">
                          <LockKeyhole className="h-8 w-8" />
                        </div>
                      </div>
                    </motion.div>
                    
                    <CardTitle className="text-3xl font-bold text-center tracking-tight">Welcome back</CardTitle>
                    <CardDescription className="text-center text-base">
                      Sign in to access your CloudBridge console
                    </CardDescription>
                  </CardHeader>

                  <CardContent className="space-y-6">
                    <form className="space-y-5" onSubmit={handleSubmit}>
                      <div className="space-y-2">
                        <Label htmlFor="email" className="text-foreground/80 dark:text-white/80 text-sm font-medium">Email address</Label>
                        <Input
                          id="email"
                          type="email"
                          autoComplete="email"
                          className="bg-muted/50 border-border text-foreground placeholder-muted-foreground focus:border-primary/50 focus:ring-primary/50 h-12 dark:bg-white/5 dark:border-white/10 dark:text-white dark:placeholder-white/30"
                          value={email}
                          onChange={(event) => setEmail(event.target.value)}
                          placeholder="you@company.com"
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <Label htmlFor="password" className="text-foreground/80 dark:text-white/80 text-sm font-medium">Password</Label>
                          <Link to="/forgot-password" className="text-sm text-primary hover:text-primary/80 transition-colors">
                            Forgot password?
                          </Link>
                        </div>
                        <Input
                          id="password"
                          type="password"
                          autoComplete="current-password"
                          className="bg-muted/50 border-border text-foreground placeholder-muted-foreground focus:border-primary/50 focus:ring-primary/50 h-12 dark:bg-white/5 dark:border-white/10 dark:text-white dark:placeholder-white/30"
                          value={password}
                          onChange={(event) => setPassword(event.target.value)}
                          placeholder="••••••••"
                          required
                        />
                      </div>

                      <AnimatePresence>
                        {error && (
                          <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm font-medium"
                          >
                            {error}
                          </motion.div>
                        )}
                      </AnimatePresence>

                      <Button
                        className="w-full h-12 bg-gradient-to-r from-primary to-blue-500 hover:from-primary/90 hover:to-blue-500/90 text-white font-semibold rounded-xl shadow-lg shadow-primary/25 transition-all duration-300 hover:shadow-primary/40 hover:scale-[1.02]"
                        type="submit"
                        disabled={isSubmitting}
                      >
                        {isSubmitting ? (
                          <motion.div
                            animate={{ rotate: 360 }}
                            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                          >
                            <Cloud className="h-5 w-5" />
                          </motion.div>
                        ) : (
                          <>
                            Sign in
                            <ArrowRight className="h-4 w-4 ml-2" />
                          </>
                        )}
                      </Button>
                    </form>

                    <div className="relative">
                      <div className="absolute inset-0 flex items-center">
                        <div className="w-full border-t border-border/10 dark:border-white/10" />
                      </div>
                      <div className="relative flex justify-center text-xs uppercase">
                        <span className="bg-card px-2 text-muted-foreground">Or continue with</span>
                      </div>
                    </div>

                    <Button
                      variant="outline"
                      className="w-full h-10 border-border bg-muted/50 hover:bg-muted text-foreground hover:text-foreground transition-colors dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10 dark:text-white dark:hover:text-white"
                      onClick={handleGoogleLogin}
                      disabled={isSubmitting}
                    >
                      <svg className="h-5 w-5 mr-2" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                      </svg>
                      {isSubmitting ? "Signing in..." : "Sign in with Google"}
                    </Button>

                    <div className="text-center text-sm text-muted-foreground pt-4 border-t border-border/10 dark:border-white/10 space-y-2">
                      <span className="flex items-center justify-center gap-2">
                        <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                        Google OAuth Authentication
                      </span>
                      <p>
                        Don't have an account?{" "}
                        <Link to="/register" className="text-primary font-medium hover:text-primary/80 transition-colors">
                          Create account
                        </Link>
                      </p>
                    </div>
                  </CardContent>
                </div>
              </Card>
            </motion.div>
          </motion.div>
        </div>
      </div>
    </main>
  );
}
