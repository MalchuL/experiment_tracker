export class ErrorResponse extends Error {
  status: number;
  message: string;
  code: string;
  constructor(status: number, message: string, code: string) {
    super(message);
    this.status = status;
    this.message = message;
    this.code = code;
  }
}

/**
 * Return a user-facing message from an API or runtime error.
 */
export function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ErrorResponse && error.message) {
    return error.message;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}
