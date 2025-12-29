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
