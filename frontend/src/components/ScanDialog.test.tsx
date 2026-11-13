// @vitest-environment jsdom
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ScanDialog from '@/components/ScanDialog';
import { ScanType } from '@/types';

function renderDialog(
  onSubmit = vi.fn().mockResolvedValue(undefined),
  onClose = vi.fn()
) {
  render(<ScanDialog open onClose={onClose} onSubmit={onSubmit} />);
  return { onSubmit, onClose };
}

describe('ScanDialog', () => {
  afterEach(cleanup);

  it('blocks submission and shows validation errors for an invalid target', async () => {
    const user = userEvent.setup();
    const { onSubmit, onClose } = renderDialog();

    await user.type(screen.getByRole('textbox', { name: /target/i }), 'bad_host');
    await user.click(screen.getByRole('button', { name: /start scan/i }));

    expect(await screen.findByText('Invalid target format')).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
    expect(onClose).not.toHaveBeenCalled();
  });

  it('relies on the required marker to block an empty target', async () => {
    const user = userEvent.setup();
    const { onSubmit } = renderDialog();

    const target = screen.getByRole('textbox', { name: /target/i });
    expect(target).toBeRequired();

    await user.click(screen.getByRole('button', { name: /start scan/i }));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('rejects a target above the host limit before calling the API', async () => {
    const user = userEvent.setup();
    const { onSubmit } = renderDialog();

    await user.type(screen.getByRole('textbox', { name: /target/i }), '10.0.0.0/8');
    await user.click(screen.getByRole('button', { name: /start scan/i }));

    expect(
      await screen.findByText('Target exceeds maximum of 1024 hosts')
    ).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('submits the form values and closes on success', async () => {
    const user = userEvent.setup();
    const { onSubmit, onClose } = renderDialog();

    await user.type(screen.getByRole('textbox', { name: /target/i }), '192.168.1.0/24');
    await user.clear(screen.getByRole('textbox', { name: /port range/i }));
    await user.type(screen.getByRole('textbox', { name: /port range/i }), '22,80,443');
    await user.click(screen.getByRole('button', { name: /start scan/i }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit).toHaveBeenCalledWith({
      target: '192.168.1.0/24',
      scan_type: ScanType.TCP_CONNECT,
      port_range: '22,80,443',
      service_detection: true,
      os_detection: false,
      aggressive: false,
    });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('shows the API error and keeps the dialog open on failure', async () => {
    const user = userEvent.setup();
    const { onSubmit, onClose } = renderDialog(
      vi.fn().mockRejectedValue(new Error('Backend unavailable'))
    );

    await user.type(screen.getByRole('textbox', { name: /target/i }), '192.168.1.10');
    await user.click(screen.getByRole('button', { name: /start scan/i }));

    expect(await screen.findByText('Backend unavailable')).toBeInTheDocument();
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onClose).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: /start scan/i })).toBeEnabled();
  });
});
