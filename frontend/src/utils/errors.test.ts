import { describe, expect, it } from 'vitest';
import { getErrorMessage } from '@/utils/errors';

describe('getErrorMessage', () => {
  it('prefers the API detail field', () => {
    const error = {
      isAxiosError: true,
      message: 'Request failed with status code 422',
      response: { data: { detail: 'Target cannot be empty' } },
    };

    expect(getErrorMessage(error, 'fallback')).toBe('Target cannot be empty');
  });

  it('falls back to the axios message without a detail', () => {
    const error = {
      isAxiosError: true,
      message: 'Network Error',
      response: { data: {} },
    };

    expect(getErrorMessage(error, 'fallback')).toBe('Network Error');
  });

  it('uses Error messages', () => {
    expect(getErrorMessage(new Error('boom'), 'fallback')).toBe('boom');
  });

  it('uses the fallback for unknown values', () => {
    expect(getErrorMessage('oops', 'fallback')).toBe('fallback');
  });
});
