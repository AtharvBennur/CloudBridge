import { FormEvent, useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight, Cloud, LockKeyhole, UserPlus } from "lucide-react";
import { Link, Navigate } from "react-router-dom";

import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { apiClient } from "@/services/apiClient";

export function RegisterPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Cloud className="h-10 w-10 text-primary animate-pulse" />
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setIsSubmitting(true);

    try {
      await apiClient.post("/auth/register", {
        email,
        password,
        display_name: displayName || email.split("@")[0],
      });
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-background via-background to-background text-foreground relative overflow-hidden">
      <div className="absolute inset-0">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary/20 rounded-full blur-[128px] animate-pulse" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-[128px] animate-pulse" style={{ animationDelay: "1s" }} />
      </div>

      <div className="absolute right-6 top-6 z-50">
        <ThemeToggle />
      </div>

      <div className="relative z-10 min-h-screen flex items-center justify-center p-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4 }}
          className="w-full max-w-md"
        >
          <Card className="border border-border/10 bg-card/50 backdrop-blur-xl shadow-2xl">
            <CardHeader className="space-y-3 pb-6">
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.2 }}
                className="flex justify-center mb-4"
              >
                <div className="relative">
                  <div className="absolute inset-0 rounded-2xl bg-primary/30 blur-xl" />
                  <div className="relative grid h-16 w-16 place-items-center rounded-2xl bg-gradient-to-br from-primary to-blue-500 text-white shadow-2xl">
                    <UserPlus className="h-8 w-8" />
                  </div>
                </div>
              </motion.div>
              <CardTitle className="text-3xl font-bold text-center tracking-tight">Create account</CardTitle>
              <CardDescription className="text-center text-base">
                Get started with CloudBridge enterprise migration platform
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-6">
              {success ? (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-center space-y-4"
                >
                  <div className="h-16 w-16 mx-auto rounded-full bg-emerald-500/10 flex items-center justify-center">
                    <Cloud className="h-8 w-8 text-emerald-500" />
                  </div>
                  <h3 className="text-lg font-semibold">Registration successful!</h3>
                  <p className="text-sm text-muted-foreground">
                    Your account has been created. You can now sign in with your credentials.
                  </p>
                  <Button asChild className="w-full">
                    <Link to="/login">
                      Sign in now
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Link>
                  </Button>
                </motion.div>
              ) : (
                <form className="space-y-4" onSubmit={handleSubmit}>
                  <div className="space-y-2">
                    <Label htmlFor="display_name">Display Name</Label>
                    <Input
                      id="display_name"
                      value={displayName}
                      onChange={(e) => setDisplayName(e.target.value)}
                      placeholder="John Doe"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="email">Email address</Label>
                    <Input
                      id="email"
                      type="email"
                      autoComplete="email"
                      className="h-12"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@company.com"
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="password">Password</Label>
                    <Input
                      id="password"
                      type="password"
                      autoComplete="new-password"
                      className="h-12"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Min. 8 characters"
                      required
                      minLength={8}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="confirm_password">Confirm Password</Label>
                    <Input
                      id="confirm_password"
                      type="password"
                      autoComplete="new-password"
                      className="h-12"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Re-enter password"
                      required
                    />
                  </div>

                  {error && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm font-medium"
                    >
                      {error}
                    </motion.div>
                  )}

                  <Button
                    className="w-full h-12 bg-gradient-to-r from-primary to-blue-500 hover:from-primary/90 hover:to-blue-500/90 text-white font-semibold rounded-xl shadow-lg"
                    type="submit"
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? "Creating account..." : (
                      <>
                        Create account
                        <ArrowRight className="ml-2 h-4 w-4" />
                      </>
                    )}
                  </Button>
                </form>
              )}

              <div className="text-center text-sm text-muted-foreground pt-4 border-t border-border/10">
                Already have an account?{" "}
                <Link to="/login" className="text-primary font-medium hover:text-primary/80 transition-colors">
                  Sign in
                </Link>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </main>
  );
}
