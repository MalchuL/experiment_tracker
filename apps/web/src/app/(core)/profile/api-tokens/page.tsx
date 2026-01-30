"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useToast } from "@/lib/hooks/use-toast";
import { apiTokensService } from "@/domain/api-tokens/services";
import type { ApiTokenCreateResponse, ApiTokenListItem } from "@/domain/api-tokens/types";

const AVAILABLE_SCOPES = [
  "projects.view",
  "projects.create",
  "projects.delete",
  "teams.manage",
  "teams.delete",
  "teams.view",
  "project.view",
  "project.edit",
  "project.delete",
  "experiments.view",
  "experiments.create",
  "experiments.edit",
  "experiments.delete",
  "hypotheses.view",
  "hypotheses.create",
  "hypotheses.edit",
  "hypotheses.delete",
  "metrics.view",
  "metrics.create",
  "metrics.edit",
  "metrics.delete",
];

const SCOPE_DESCRIPTIONS: Record<string, string> = {
  "projects.view": "View all projects available to the user.",
  "projects.create": "Create new projects within a team.",
  "projects.delete": "Delete projects.",
  "teams.manage": "Manage team members and settings.",
  "teams.delete": "Delete teams.",
  "teams.view": "View team details.",
  "project.view": "View a single project.",
  "project.edit": "Edit a project.",
  "project.delete": "Delete a single project.",
  "experiments.view": "View experiments in a project.",
  "experiments.create": "Create experiments.",
  "experiments.edit": "Edit experiments.",
  "experiments.delete": "Delete experiments.",
  "hypotheses.view": "View hypotheses.",
  "hypotheses.create": "Create hypotheses.",
  "hypotheses.edit": "Edit hypotheses.",
  "hypotheses.delete": "Delete hypotheses.",
  "metrics.view": "View metrics.",
  "metrics.create": "Create metrics.",
  "metrics.edit": "Edit metrics.",
  "metrics.delete": "Delete metrics.",
};

export default function ApiTokensPage() {
  const { toast } = useToast();
  const [tokens, setTokens] = useState<ApiTokenListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createdToken, setCreatedToken] = useState<ApiTokenCreateResponse | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [expiresInDays, setExpiresInDays] = useState("");
  const [selectedScopes, setSelectedScopes] = useState<string[]>(AVAILABLE_SCOPES);

  const scopesByGroup = useMemo(() => {
    return AVAILABLE_SCOPES;
  }, []);

  const loadTokens = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await apiTokensService.list();
      setTokens(data);
    } catch (error) {
      toast({
        title: "Failed to load tokens",
        description: "Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    loadTokens();
  }, [loadTokens]);

  const handleToggleScope = (scope: string) => {
    setSelectedScopes((current) =>
      current.includes(scope)
        ? current.filter((item) => item !== scope)
        : [...current, scope],
    );
  };

  const handleCreateToken = async () => {
    if (!name.trim()) {
      toast({
        title: "Name is required",
        description: "Provide a name for the token.",
        variant: "destructive",
      });
      return;
    }
    setIsSubmitting(true);
    try {
      const expires = expiresInDays.trim() ? Number(expiresInDays) : undefined;
      const token = await apiTokensService.create({
        name: name.trim(),
        description: description.trim() || undefined,
        scopes: selectedScopes,
        expiresInDays: Number.isFinite(expires) ? expires : undefined,
      });
      setCreatedToken(token);
      setName("");
      setDescription("");
      setExpiresInDays("");
      setSelectedScopes(AVAILABLE_SCOPES);
      await loadTokens();
      toast({
        title: "Token created",
        description: "Copy the token now. It will only be shown once.",
      });
    } catch (error) {
      toast({
        title: "Failed to create token",
        description: "Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRevokeToken = async (tokenId: string) => {
    try {
      await apiTokensService.revoke(tokenId);
      await loadTokens();
      toast({
        title: "Token revoked",
        description: "The token has been revoked.",
      });
    } catch (error) {
      toast({
        title: "Failed to revoke token",
        description: "Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleCopyToken = async () => {
    if (!createdToken) return;
    try {
      await navigator.clipboard.writeText(createdToken.token);
      toast({
        title: "Token copied",
        description: "The token has been copied to the clipboard.",
      });
    } catch (error) {
      toast({
        title: "Copy failed",
        description: "Copy the token manually.",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="API Tokens"
        description="Create personal API tokens for training scripts and SDK usage."
      />

      {createdToken && (
        <Alert>
          <AlertTitle>Token created</AlertTitle>
          <AlertDescription>
            <div className="space-y-2">
              <p>Copy this token now. You will not be able to view it again.</p>
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                <code className="rounded bg-muted px-2 py-1 text-xs break-all">
                  {createdToken.token}
                </code>
                <Button type="button" variant="secondary" onClick={handleCopyToken}>
                  Copy
                </Button>
              </div>
            </div>
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Create token</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-medium">Name</label>
              <Input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Training cluster token"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Expires in days (optional)</label>
              <Input
                value={expiresInDays}
                onChange={(event) => setExpiresInDays(event.target.value)}
                placeholder="30"
                type="number"
                min={1}
              />
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Description</label>
            <Textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Optional description"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Scopes</label>
            <div className="grid gap-2 md:grid-cols-2">
              {scopesByGroup.map((scope) => (
                <label key={scope} className="flex items-start gap-2 text-sm">
                  <Checkbox
                    checked={selectedScopes.includes(scope)}
                    onCheckedChange={() => handleToggleScope(scope)}
                  />
                  <span>
                    <span className="font-medium">{scope}</span>
                    <span className="block text-xs text-muted-foreground">
                      {SCOPE_DESCRIPTIONS[scope] ?? "Controls API access for this action."}
                    </span>
                  </span>
                </label>
              ))}
            </div>
          </div>
          <Button onClick={handleCreateToken} disabled={isSubmitting}>
            {isSubmitting ? "Creating..." : "Create token"}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Existing tokens</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading tokens...</p>
          ) : tokens.length === 0 ? (
            <p className="text-sm text-muted-foreground">No tokens yet.</p>
          ) : (
            <div className="space-y-4">
              {tokens.map((token) => (
                <div
                  key={token.id}
                  className="flex flex-col gap-2 rounded border p-3 md:flex-row md:items-center md:justify-between"
                >
                  <div>
                    <p className="text-sm font-medium">{token.name}</p>
                    <p className="text-xs text-muted-foreground">
                      Scopes: {token.scopes.join(", ") || "none"}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Created: {new Date(token.createdAt).toLocaleString()}
                    </p>
                    {token.expiresAt && (
                      <p className="text-xs text-muted-foreground">
                        Expires: {new Date(token.expiresAt).toLocaleString()}
                      </p>
                    )}
                    {token.lastUsedAt && (
                      <p className="text-xs text-muted-foreground">
                        Last used: {new Date(token.lastUsedAt).toLocaleString()}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {token.revoked ? (
                      <span className="text-xs text-destructive">Revoked</span>
                    ) : (
                      <Button
                        variant="destructive"
                        onClick={() => handleRevokeToken(token.id)}
                      >
                        Revoke
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
