/**
 * Extract user-friendly error message from login/register API errors.
 * FastAPI returns detail as string or array of strings; Axios wraps in response.data.
 */
export function getAuthErrorMessage(
  e: unknown,
  fallback: string = 'Something went wrong'
): string {
  if (!e || typeof e !== 'object' || !('response' in e)) {
    const err = e as Error | undefined;
    if (err?.message) {
      if (err.message.includes('timeout') || err.message.includes('Network Error')) {
        return 'Backend unreachable. Check that the server is running and the IP in lib/config.ts is correct.';
      }
      return err.message;
    }
    return fallback;
  }
  const res = (e as { response?: { data?: { detail?: string | string[] }; status?: number } }).response;
  if (!res?.data) return fallback;
  const detail = res.data.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    return typeof first === 'object' && first !== null && 'msg' in first
      ? String((first as { msg: string }).msg)
      : String(first);
  }
  if (res.status === 401) return 'Invalid email or password.';
  if (res.status === 400) return 'Invalid request. Check your input.';
  if (res.status && res.status >= 500) return 'Server error. Try again later.';
  return fallback;
}
