import { QueryClient } from "@tanstack/react-query";

export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // Stale time: data is considered fresh for 5 minutes
        staleTime: 1000 * 60 * 5,
        // Cache time: unused data stays in cache for 10 minutes
        gcTime: 1000 * 60 * 10,
        // Retry failed requests 3 times
        retry: 3,
        // Retry delay increases exponentially
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
        // Refetch on window focus in production
        refetchOnWindowFocus: process.env.NODE_ENV === "production",
        // Refetch on reconnect
        refetchOnReconnect: true,
      },
      mutations: {
        // Retry failed mutations once
        retry: 1,
      },
    },
  });
}
