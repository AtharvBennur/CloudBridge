import { FormEvent, useState } from "react";
import { motion } from "framer-motion";
import { ArrowLeft, Cloud, KeyRound, Mail } from "lucide-react";
import { Link } from "react-router-dom";

import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      // In production, this would call the backend password reset endpoint
      // For now, we simulate success since the backend doesn't have this endpoint yet
      await new Promise((resolve) => setTimeout(resolve, 1000));
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send reset link.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-background via-background to-background text-foreground relative overflow-hidden">
      <div className="absolute inset-0">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary/20 rounded-full blur-[128px] animate-pulse" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-[128px] animate-pulse" style={{ animationDelay: "1s" }} />
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
                  <div className="absolute inset-0 rounded-2xl bg-amber-500/30 blur-xl" />
                  <div className="relative grid h-16 w-16 place-items-center rounded-2xl bg-gradient-to-br from-amber-500 to-orange-600 text-white shadow-2xl">
                    <KeyRound className="h-8 w-8" />
                  </div>
                </div>
              </motion.div>
              <CardTitle className="text-3xl font-bold text-center tracking-tight">Reset password</CardTitle>
              <CardDescription className="text-center text-base">
                Enter your email and we'll send you a link to reset your password
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-6">
              {sent ? (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-center space-y-4"
                >
                  <div className="h-16 w-16 mx-auto rounded-full bg-emerald-500/10 flex items-center justify-center">
                    <Mail className="h-8 w-8 text-emerald-500" />
                  </div>
                  <h3 className="text-lg font-semibold">Check your email</h3>
                  <p className="text-sm text-muted-foreground">
                    We've sent a password reset link to <strong className="text-foreground">{email}</strong>. Please check your inbox and follow the instructions.
                  </p>
                  <Button variant="outline" asChild className="w-full">
                    <Link to="/login">
                      <ArrowLeft className="mr-2 h-4 w-4" />
                      Back to sign in
                    </Link>
                  </Button>
                </motion.div>
              ) : (
                <form className="space-y-4" onSubmit={handleSubmit}>
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
                    className="w-full h-12 bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-500/90 hover:to-orange-600/90 text-white font-semibold rounded-xl shadow-lg"
                    type="submit"
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? "Sending reset link..." : (
                      <>
                        Send reset link
                        <Mail className="ml-2 h-4 w-4" />
                      </>
                    )}
                  </Button>
                </form>
              )}

              <div className="text-center text-sm text-muted-foreground pt-4 border-t border-border/10">
                <Link to="/login" className="text-primary font-medium hover:text-primary/80 transition-colors inline-flex items-center gap-1">
                  <ArrowLeft className="h-3.5 w-3.5" />
                  Back to sign in
                </Link>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </main>
  );
}
