import {
  BookOpen,
  Keyboard,
  HelpCircle,
  FileText,
  Server,
  Mail,
  ExternalLink,
  ArrowRight,
  Database,
  Cloud,
  Lock,
  Activity,
  GitBranch,
  Settings,
  Search,
  ChevronRight,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const shortcuts = [
  { keys: ["G", "D"], description: "Go to Dashboard" },
  { keys: ["G", "M"], description: "Go to Migrations" },
  { keys: ["G", "S"], description: "Go to Settings" },
  { keys: ["G", "N"], description: "Go to Notifications" },
  { keys: ["G", "O"], description: "Go to Observability" },
  { keys: ["?"], description: "Open Help" },
  { keys: ["Esc"], description: "Close dialog / cancel" },
];

const faqItems = [
  {
    question: "How do I connect my AWS account?",
    answer:
      "Navigate to the AWS Connections page from the sidebar. Click 'Add Connection' and provide your AWS credentials. CloudBridge uses STS AssumeRole for secure, cross-account access without storing long-lived keys.",
  },
  {
    question: "What database engines are supported?",
    answer:
      "CloudBridge supports MySQL, PostgreSQL, Oracle, and SQL Server as both source and target databases. Aurora (MySQL and PostgreSQL compatible) is also fully supported.",
  },
  {
    question: "How does schema drift detection work?",
    answer:
      "CloudBridge periodically compares the source and target database schemas. When differences are detected beyond expected migration changes, it flags them on the Schema Drift page for your review.",
  },
  {
    question: "Can I pause and resume a running migration?",
    answer:
      "Yes. Running migrations can be paused from the migration detail page. All progress is checkpointed, so resuming picks up exactly where you left off without data duplication.",
  },
  {
    question: "How are credentials stored?",
    answer:
      "Database credentials are encrypted and stored in your configured Secrets Manager. CloudBridge never stores plaintext passwords. All API communication uses TLS.",
  },
  {
    question: "What is the approval workflow?",
    answer:
      "For production migrations, CloudBridge can require manual approval before starting. Approvers receive notifications and can review the migration plan before granting access.",
  },
];

const quickStartSteps = [
  {
    step: 1,
    title: "Connect your AWS account",
    description: "Add an AWS connection with STS AssumeRole credentials.",
    icon: Cloud,
    link: "/aws-connections",
  },
  {
    step: 2,
    title: "Register databases",
    description: "Configure source and target database connections with encrypted credentials.",
    icon: Database,
    link: "/database-configs",
  },
  {
    step: 3,
    title: "Create a migration",
    description: "Define a migration job specifying source, target, and migration type.",
    icon: GitBranch,
    link: "/migrations/new",
  },
  {
    step: 4,
    title: "Run preflight checks",
    description: "Validate connectivity, permissions, and schema compatibility.",
    icon: Search,
    link: "/preflight",
  },
  {
    step: 5,
    title: "Start migration",
    description: "Launch the migration and monitor progress in real time.",
    icon: Activity,
    link: "/migrations",
  },
];

const docLinks = [
  {
    title: "Architecture Overview",
    description: "Understand the CloudBridge system architecture and components.",
    icon: Server,
    href: "#architecture",
  },
  {
    title: "Migration Guide",
    description: "Step-by-step guide to running database migrations.",
    icon: GitBranch,
    href: "#",
  },
  {
    title: "Security Model",
    description: "How CloudBridge handles authentication and encryption.",
    icon: Lock,
    href: "#",
  },
  {
    title: "CDC Configuration",
    description: "Setting up Change Data Capture for ongoing replication.",
    icon: Activity,
    href: "#",
  },
];

export function HelpPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Help Center</h1>
        <p className="text-muted-foreground mt-2">
          Documentation, guides, and reference for using CloudBridge.
        </p>
      </div>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <BookOpen className="h-5 w-5" />
          Quick Start Guide
        </h2>
        <p className="text-sm text-muted-foreground">
          Follow these steps to run your first database migration in under 10
          minutes.
        </p>
        <div className="space-y-3">
          {quickStartSteps.map((item) => (
            <div
              key={item.step}
              className="flex items-start gap-4 p-4 border border-border/70 rounded-2xl bg-background/50 hover:bg-muted/20 transition"
            >
              <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
                <item.icon className="h-5 w-5 text-primary" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">Step {item.step}</Badge>
                  <h4 className="font-semibold text-sm">{item.title}</h4>
                </div>
                <p className="text-sm text-muted-foreground mt-1">
                  {item.description}
                </p>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground mt-3 shrink-0" />
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <Keyboard className="h-5 w-5" />
          Keyboard Shortcuts
        </h2>
        <Card className="border-border/70">
          <CardContent className="pt-6">
            <div className="space-y-3">
              {shortcuts.map((shortcut) => (
                <div
                  key={shortcut.description}
                  className="flex items-center justify-between py-2 border-b border-border/50 last:border-0"
                >
                  <span className="text-sm">{shortcut.description}</span>
                  <div className="flex gap-1">
                    {shortcut.keys.map((key) => (
                      <kbd
                        key={key}
                        className="inline-flex items-center justify-center h-7 min-w-[1.75rem] px-1.5 rounded-lg border border-border/70 bg-muted/50 text-xs font-mono font-semibold"
                      >
                        {key}
                      </kbd>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <HelpCircle className="h-5 w-5" />
          Frequently Asked Questions
        </h2>
        <div className="space-y-3">
          {faqItems.map((item) => (
            <Card key={item.question} className="border-border/70">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">{item.question}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">{item.answer}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <FileText className="h-5 w-5" />
          Documentation
        </h2>
        <div className="grid gap-4 md:grid-cols-2">
          {docLinks.map((link) => (
            <a
              key={link.title}
              href={link.href}
              className="flex items-start gap-4 p-4 border border-border/70 rounded-2xl bg-background/50 hover:bg-muted/20 transition group"
            >
              <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
                <link.icon className="h-5 w-5 text-primary" />
              </div>
              <div className="flex-1">
                <h4 className="font-semibold text-sm">{link.title}</h4>
                <p className="text-xs text-muted-foreground mt-1">
                  {link.description}
                </p>
              </div>
              <ExternalLink className="h-4 w-4 text-muted-foreground mt-1 shrink-0 opacity-0 group-hover:opacity-100 transition" />
            </a>
          ))}
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <Server className="h-5 w-5" />
          Architecture Overview
        </h2>
        <Card className="border-border/70">
          <CardContent className="pt-6 space-y-4">
            <p className="text-sm text-muted-foreground">
              CloudBridge follows a three-tier architecture for secure database
              migration orchestration:
            </p>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="p-4 rounded-xl border border-border/50">
                <h4 className="font-semibold text-sm mb-2">Frontend</h4>
                <p className="text-xs text-muted-foreground">
                  React SPA with TypeScript. Communicates with the backend API
                  for all operations. Runs in your browser.
                </p>
              </div>
              <div className="p-4 rounded-xl border border-border/50">
                <h4 className="font-semibold text-sm mb-2">Backend API</h4>
                <p className="text-xs text-muted-foreground">
                  Flask REST API handling business logic, authentication, and
                  orchestration. Manages metadata and coordinates workers.
                </p>
              </div>
              <div className="p-4 rounded-xl border border-border/50">
                <h4 className="font-semibold text-sm mb-2">ECS Workers</h4>
                <p className="text-xs text-muted-foreground">
                  Docker containers running on AWS ECS Fargate. Execute the
                  actual data movement between databases within your VPC.
                </p>
              </div>
            </div>
            <div className="p-4 rounded-xl border border-border/50 bg-muted/20">
              <h4 className="font-semibold text-sm mb-2">Security Model</h4>
              <p className="text-xs text-muted-foreground">
                All database credentials are stored in AWS Secrets Manager.
                CloudBridge uses STS AssumeRole for cross-account access. No
                plaintext secrets are ever stored or logged. All API traffic is
                encrypted with TLS.
              </p>
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <Mail className="h-5 w-5" />
          Contact & Support
        </h2>
        <Card className="border-border/70">
          <CardContent className="pt-6 space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="p-4 rounded-xl border border-border/50">
                <h4 className="font-semibold text-sm mb-1">Email Support</h4>
                <p className="text-xs text-muted-foreground">
                  support@cloudbridge.io
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Response within 24 hours for enterprise plans.
                </p>
              </div>
              <div className="p-4 rounded-xl border border-border/50">
                <h4 className="font-semibold text-sm mb-1">Issue Tracker</h4>
                <p className="text-xs text-muted-foreground">
                  Report bugs or request features through the issue tracker.
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  github.com/cloudbridge/issues
                </p>
              </div>
              <div className="p-4 rounded-xl border border-border/50">
                <h4 className="font-semibold text-sm mb-1">Status Page</h4>
                <p className="text-xs text-muted-foreground">
                  Check system status and incident history.
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  status.cloudbridge.io
                </p>
              </div>
              <div className="p-4 rounded-xl border border-border/50">
                <h4 className="font-semibold text-sm mb-1">Enterprise Support</h4>
                <p className="text-xs text-muted-foreground">
                  Dedicated Slack channel and priority support for enterprise
                  customers.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
