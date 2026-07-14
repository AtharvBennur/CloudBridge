/*
Purpose:
A premium dark-themed login screen.
*/

import { FormEvent, useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight, Cloud, LockKeyhole, Sparkles } from "lucide-react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { env } from "@/lib/env";

interface LocationState {
  from?: {
    pathname?: string;
  };
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
      <div className="flex min-h-screen items-center justify-center bg-[#0B0F17] text-white">
        <div className="flex flex-col items-center gap-3">
          <Cloud className="h-8 w-8 text-primary animate-pulse" />
          <p className="text-sm font-medium tracking-wide">Preparing secure session...</p>
        </div>
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  const isCognitoPrepared = Boolean(
    env.cognitoRegion && env.cognitoUserPoolId && env.cognitoClientId,
  );

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await login({ email, password });
      navigate(redirectTo, { replace: true });
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : "Unable to sign in.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#0B0F17] text-[#F3F4F6] relative overflow-hidden flex items-center justify-center">
      {/* Background glow effects */}
      <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] rounded-full bg-primary/20 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-blue-500/10 blur-[120px] pointer-events-none" />

      <div className="absolute right-4 top-4">
        <ThemeToggle />
      </div>

      <div className="w-full max-w-6xl grid lg:grid-cols-[1.1fr_0.9fr] gap-12 p-6 z-10">
        {/* Left Branding Panel */}
        <section className="hidden lg:flex flex-col justify-between p-8">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-primary to-blue-500 text-white shadow-lg">
              <Cloud className="h-5 w-5" />
            </div>
            <div>
              <p className="font-semibold text-lg tracking-tight">CloudBridge</p>
              <p className="text-xs text-muted-foreground">SaaS Migration Plane</p>
            </div>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="max-w-md space-y-4"
          >
            <div className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 border border-primary/20 px-3 py-1 text-xs font-semibold text-primary">
              <Sparkles className="h-3 w-3" />
              Sprint 5 Platform
            </div>
            <h1 className="text-5xl font-semibold leading-tight tracking-tight text-white">
              Enterprise Cloud Database Migrations.
            </h1>
            <p className="text-muted-foreground text-base leading-relaxed">
              Orchestrate cross-account database migrations with automated STS AssumeRole credentials testing and AWS Secrets Manager integration.
            </p>
          </motion.div>

          <div className="grid grid-cols-3 gap-3 text-xs text-muted-foreground">
            {["STS AssumeRole", "Secrets Protection", "Migration Workers"].map((item) => (
              <div key={item} className="rounded-xl border border-white/5 bg-white/[0.02] p-3 text-center backdrop-blur">
                <p className="font-medium text-foreground">{item}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Right Form Card */}
        <section className="flex items-center justify-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4 }}
            className="w-full max-w-md"
          >
            <Card className="border-white/10 bg-white/[0.03] backdrop-blur-xl shadow-2xl relative overflow-hidden">
              {/* Subtle top light bar */}
              <div className="absolute top-0 left-0 right-0 h-[1.5px] bg-gradient-to-r from-transparent via-primary/50 to-transparent" />
              
              <CardHeader className="space-y-2">
                <div className="mb-2 grid h-10 w-10 place-items-center rounded-xl bg-primary/10 text-primary">
                  <LockKeyhole className="h-5 w-5" />
                </div>
                <CardTitle className="text-2xl font-bold tracking-tight text-white">Sign in to console</CardTitle>
                <CardDescription className="text-muted-foreground">
                  Sign in using your CloudBridge identity credentials.
                </CardDescription>
              </CardHeader>
              
              <CardContent className="pt-2">
                <form className="space-y-4" onSubmit={handleSubmit}>
                  <div className="space-y-2">
                    <Label htmlFor="email" className="text-white/80">Work Email</Label>
                    <Input
                      id="email"
                      type="email"
                      autoComplete="email"
                      className="bg-white/[0.04] border-white/10 text-white placeholder-white/20 focus:border-primary/50"
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                      placeholder="name@company.com"
                      required
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="password" className="text-white/80">Password</Label>
                    </div>
                    <Input
                      id="password"
                      type="password"
                      autoComplete="current-password"
                      className="bg-white/[0.04] border-white/10 text-white placeholder-white/20 focus:border-primary/50"
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      placeholder="••••••••"
                      required
                    />
                  </div>

                  {error && (
                    <p className="text-sm text-red-400 font-medium bg-red-500/10 border border-red-500/20 p-2.5 rounded-xl">
                      {error}
                    </p>
                  )}

                  <Button className="w-full mt-2 bg-primary hover:bg-primary/95 text-white py-6 rounded-xl font-semibold" type="submit" disabled={isSubmitting}>
                    {isSubmitting ? "Signing in..." : "Continue to Dashboard"}
                    <ArrowRight className="h-4.5 w-4.5 ml-2" />
                  </Button>
                </form>

                <div className="mt-6 flex items-center justify-between text-xs text-muted-foreground border-t border-white/5 pt-4">
                  <span>Identity Engine: {isCognitoPrepared ? "Cognito (Active)" : "Secure Local Sandbox"}</span>
                  <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </section>
      </div>
    </main>
  );
}
