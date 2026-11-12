import axios from 'axios';

interface ApiErrorBody {
  detail?: unknown;
}

/** Extract a user-facing message from Axios/JS errors without leaking internals. */
export function getErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const body = error.response?.data as ApiErrorBody | undefined;
    if (typeof body?.detail === 'string' && body.detail.length > 0) {
      return body.detail;
    }
    return error.message || fallback;
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}
