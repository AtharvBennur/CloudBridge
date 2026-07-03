import { FormEvent, useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight, Cloud, LockKeyhole } from "lucide-react";
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
  const { isAuthenticated, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const locationState = location.state as LocationState | null;
  const redirectTo = locationState?.from?.pathname || "/dashboard";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

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
    <main className="min-h-screen bg-background">
      <div className="absolute right-4 top-4">
        <ThemeToggle />
      </div>

      <div className="grid min-h-screen lg:grid-cols-[1.1fr_0.9fr]">
        <section className="hidden border-r bg-card px-10 py-12 lg:flex lg:flex-col lg:justify-between">
          <div className="flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-lg bg-primary text-primary-foreground">
              <Cloud className="h-5 w-5" />
            </div>
            <div>
              <p className="font-semibold">CloudBridge</p>
              <p className="text-sm text-muted-foreground">Operational foundation</p>
            </div>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45 }}
            className="max-w-xl"
          >
            <p className="mb-5 text-sm font-semibold uppercase text-primary">Sprint 1</p>
            <h1 className="text-5xl font-semibold leading-tight">
              A secure console foundation for the work ahead.
            </h1>
            <p className="mt-5 text-lg text-muted-foreground">
              Sign in to validate routing, theming, API health, and dashboard readiness before
              Cognito is connected.
            </p>
          </motion.div>

          <div className="grid grid-cols-3 gap-3 text-sm">
            {["Protected routes", "Health API", "Dark mode"].map((item) => (
              <div key={item} className="rounded-lg border bg-background p-4">
                <p className="font-medium">{item}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="flex items-center justify-center px-4 py-20">
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.35 }}
            className="w-full max-w-md"
          >
            <Card>
              <CardHeader>
                <div className="mb-3 grid h-11 w-11 place-items-center rounded-lg bg-secondary text-secondary-foreground">
                  <LockKeyhole className="h-5 w-5" />
                </div>
                <CardTitle>Sign in</CardTitle>
                <CardDescription>
                  Use a local Sprint 1 session. Cognito variables are already reserved.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form className="space-y-4" onSubmit={handleSubmit}>
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      type="email"
                      autoComplete="email"
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="password">Password</Label>
                    <Input
                      id="password"
                      type="password"
                      autoComplete="current-password"
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      required
                    />
                  </div>

                  {error ? <p className="text-sm text-destructive">{error}</p> : null}

                  <Button className="w-full" type="submit" disabled={isSubmitting}>
                    {isSubmitting ? "Signing in" : "Continue"}
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </form>

                <div className="mt-5 rounded-md border bg-muted p-3 text-sm text-muted-foreground">
                  Cognito configuration: {isCognitoPrepared ? "environment detected" : "pending"}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </section>
      </div>
    </main>
  );
}
