"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ENTITY_NAME_MAX_LEN } from "@/lib/validation/entity-limits";
import { ChevronDown } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useAuth } from "@/domain/auth/hooks";
import { authService } from "@/domain/auth/services";
import { useToast } from "@/lib/hooks/use-toast";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";

const accountSchema = z.object({
  email: z.string().email(),
  displayName: z.string().max(ENTITY_NAME_MAX_LEN),
  avatarUrl: z.union([z.literal(""), z.string().url("Enter a valid URL or leave blank")]),
});

type AccountFormValues = z.infer<typeof accountSchema>;

const passwordSchema = z
  .object({
    currentPassword: z.string().min(1, "Required"),
    newPassword: z.string().min(8, "At least 8 characters"),
    confirmPassword: z.string().min(1, "Required"),
  })
  .refine((d) => d.newPassword === d.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

type PasswordFormValues = z.infer<typeof passwordSchema>;

export default function ProfilePage() {
  const { user, updateUser } = useAuth();
  const { toast } = useToast();
  const [accountPending, setAccountPending] = useState(false);
  const [passwordPending, setPasswordPending] = useState(false);

  const accountForm = useForm<AccountFormValues>({
    resolver: zodResolver(accountSchema as any),
    defaultValues: {
      email: "",
      displayName: "",
      avatarUrl: "",
    },
  });

  const passwordForm = useForm<PasswordFormValues>({
    resolver: zodResolver(passwordSchema as any),
    defaultValues: {
      currentPassword: "",
      newPassword: "",
      confirmPassword: "",
    },
  });

  useEffect(() => {
    if (!user) return;
    accountForm.reset({
      email: user.email,
      displayName: user.displayName ?? "",
      avatarUrl: user.avatarUrl ?? "",
    });
  }, [user, accountForm]);

  const onSaveAccount = async (values: AccountFormValues) => {
    setAccountPending(true);
    try {
      await updateUser({
        email: values.email,
        displayName: values.displayName.trim() || null,
        avatarUrl: values.avatarUrl.trim() || null,
      });
      toast({ title: "Profile updated" });
    } catch {
      toast({
        title: "Could not update profile",
        description: "Check your input and try again.",
        variant: "destructive",
      });
    } finally {
      setAccountPending(false);
    }
  };

  const onChangePassword = async (values: PasswordFormValues) => {
    setPasswordPending(true);
    try {
      await authService.changePassword({
        currentPassword: values.currentPassword,
        newPassword: values.newPassword,
      });
      passwordForm.reset();
      toast({ title: "Password updated" });
    } catch {
      toast({
        title: "Could not update password",
        description: "Check your current password and try again.",
        variant: "destructive",
      });
    } finally {
      setPasswordPending(false);
    }
  };

  if (!user) {
    return (
      <div className="container mx-auto max-w-2xl space-y-6 p-6">
        <p className="text-sm text-muted-foreground">Loading profile…</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto max-w-2xl space-y-6 p-6">
      <PageHeader
        title="Profile"
        description="Your account details, password, and links to API tokens."
      />

      <Card>
        <CardHeader>
          <CardTitle>Account</CardTitle>
          <CardDescription>Email, display name, and optional avatar image URL.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <dl className="grid gap-2 text-sm">
            <div className="flex flex-col gap-0.5 sm:flex-row sm:gap-4">
              <dt className="text-muted-foreground sm:w-40">User ID</dt>
              <dd className="font-mono text-xs break-all">{user.id}</dd>
            </div>
            {user.createdAt ? (
              <div className="flex flex-col gap-0.5 sm:flex-row sm:gap-4">
                <dt className="text-muted-foreground sm:w-40">Member since</dt>
                <dd>{new Date(user.createdAt).toLocaleString()}</dd>
              </div>
            ) : null}
            <div className="flex flex-col gap-0.5 sm:flex-row sm:gap-4">
              <dt className="text-muted-foreground sm:w-40">Status</dt>
              <dd>
                {user.isVerified ? "Verified" : "Not verified"} ·{" "}
                {user.isActive ? "Active" : "Inactive"}
              </dd>
            </div>
          </dl>

          <Form {...accountForm}>
            <form onSubmit={accountForm.handleSubmit(onSaveAccount)} className="space-y-4">
              <FormField
                control={accountForm.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Email</FormLabel>
                    <FormControl>
                      <Input type="email" autoComplete="email" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={accountForm.control}
                name="displayName"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Display name</FormLabel>
                    <FormControl>
                      <Input autoComplete="name" placeholder="Your name" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={accountForm.control}
                name="avatarUrl"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Avatar URL</FormLabel>
                    <FormControl>
                      <Input
                        type="url"
                        placeholder="https://…"
                        autoComplete="off"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <Button type="submit" disabled={accountPending}>
                {accountPending ? "Saving…" : "Save changes"}
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>

      <Collapsible defaultOpen={false}>
        <Card>
          <CardHeader className="p-0">
            <CollapsibleTrigger asChild>
              <button
                type="button"
                className="flex w-full items-center justify-between gap-4 rounded-t-xl p-6 text-left outline-none transition-colors hover:bg-muted/50 focus-visible:ring-2 focus-visible:ring-ring group"
              >
                <div>
                  <p className="text-2xl font-semibold leading-none tracking-tight">Change password</p>
                  <p className="mt-1.5 text-sm text-muted-foreground">
                    Requires your current password. Not available when using an API token for
                    authentication.
                  </p>
                </div>
                <ChevronDown className="h-5 w-5 shrink-0 text-muted-foreground transition-transform duration-200 group-data-[state=open]:rotate-180" />
              </button>
            </CollapsibleTrigger>
          </CardHeader>
          <CollapsibleContent>
            <CardContent>
              <Form {...passwordForm}>
                <form
                  onSubmit={passwordForm.handleSubmit(onChangePassword)}
                  className="space-y-4"
                >
                  <FormField
                    control={passwordForm.control}
                    name="currentPassword"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Current password</FormLabel>
                        <FormControl>
                          <Input type="password" autoComplete="current-password" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={passwordForm.control}
                    name="newPassword"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>New password</FormLabel>
                        <FormControl>
                          <Input type="password" autoComplete="new-password" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={passwordForm.control}
                    name="confirmPassword"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Confirm new password</FormLabel>
                        <FormControl>
                          <Input type="password" autoComplete="new-password" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <Button type="submit" disabled={passwordPending}>
                    {passwordPending ? "Saving…" : "Update password"}
                  </Button>
                </form>
              </Form>
            </CardContent>
          </CollapsibleContent>
        </Card>
      </Collapsible>

      <p className="text-sm text-muted-foreground">
        <Link
          href={FRONTEND_ROUTES.PROFILE_API_TOKENS}
          className="underline underline-offset-4"
        >
          API tokens
        </Link>{" "}
        for training scripts and the SDK.
      </p>
    </div>
  );
}
