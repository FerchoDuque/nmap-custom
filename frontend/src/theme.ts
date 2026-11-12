import { alpha, createTheme } from '@mui/material';

export const CYAN = '#00e5ff';
export const CYAN_DIM = '#00b8cc';
export const BG_DEFAULT = '#02040a';
export const BG_PAPER = '#071018';

const MONO_FONT =
  '"Share Tech Mono", "JetBrains Mono", "Fira Code", "Consolas", "Courier New", monospace';

export function createAppTheme() {
  return createTheme({
    palette: {
      mode: 'dark',
      primary: {
        main: CYAN,
        dark: CYAN_DIM,
        light: '#6ffcff',
        contrastText: '#001014',
      },
      secondary: {
        main: '#00ffa3',
      },
      success: { main: '#00ff9c' },
      warning: { main: '#ffd166' },
      error: { main: '#ff4d6d' },
      info: { main: CYAN },
      background: {
        default: BG_DEFAULT,
        paper: BG_PAPER,
      },
      text: {
        primary: '#d7fff7',
        secondary: alpha(CYAN, 0.72),
      },
      divider: alpha(CYAN, 0.18),
    },
    typography: {
      fontFamily: MONO_FONT,
      h1: { fontWeight: 700, letterSpacing: '0.04em' },
      h2: { fontWeight: 700, letterSpacing: '0.04em' },
      h3: { fontWeight: 700, letterSpacing: '0.03em', textTransform: 'uppercase' },
      h4: { fontWeight: 600, letterSpacing: '0.03em' },
      h5: { fontWeight: 600, letterSpacing: '0.02em' },
      h6: { fontWeight: 600, letterSpacing: '0.02em' },
      button: { fontWeight: 700, letterSpacing: '0.08em' },
    },
    shape: { borderRadius: 2 },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            backgroundColor: BG_DEFAULT,
            backgroundImage:
              'radial-gradient(circle at 50% 0%, rgba(0,229,255,0.08), transparent 35%), linear-gradient(rgba(0,229,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0,229,255,0.03) 1px, transparent 1px)',
            backgroundSize: 'auto, 32px 32px, 32px 32px',
            backgroundAttachment: 'fixed',
          },
          '*::selection': {
            backgroundColor: alpha(CYAN, 0.3),
            color: '#eaffff',
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            backgroundImage: 'none',
            border: `1px solid ${alpha(CYAN, 0.22)}`,
            boxShadow: `0 0 0 1px ${alpha(CYAN, 0.06)} inset, 0 0 24px ${alpha(CYAN, 0.06)}`,
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            backgroundImage: 'none',
            backgroundColor: alpha(BG_PAPER, 0.92),
            border: `1px solid ${alpha(CYAN, 0.25)}`,
            boxShadow: `0 0 0 1px ${alpha(CYAN, 0.05)} inset, 0 0 18px ${alpha(CYAN, 0.08)}`,
            transition: 'border-color 120ms linear, box-shadow 120ms linear',
            '&:hover': {
              borderColor: alpha(CYAN, 0.5),
              boxShadow: `0 0 0 1px ${alpha(CYAN, 0.08)} inset, 0 0 24px ${alpha(CYAN, 0.16)}`,
            },
          },
        },
      },
      MuiAppBar: {
        styleOverrides: {
          root: {
            backgroundImage: 'none',
            backgroundColor: alpha('#03070c', 0.9),
            borderBottom: `1px solid ${alpha(CYAN, 0.25)}`,
            boxShadow: `0 0 20px ${alpha(CYAN, 0.12)}`,
          },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: {
            borderRadius: 2,
            textTransform: 'uppercase',
          },
          containedPrimary: {
            boxShadow: `0 0 12px ${alpha(CYAN, 0.35)}`,
            '&:hover': {
              boxShadow: `0 0 18px ${alpha(CYAN, 0.55)}`,
            },
          },
          outlined: {
            borderColor: alpha(CYAN, 0.5),
            '&:hover': {
              borderColor: CYAN,
              backgroundColor: alpha(CYAN, 0.08),
            },
          },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: {
            borderRadius: 2,
            fontFamily: 'inherit',
            border: `1px solid ${alpha(CYAN, 0.25)}`,
          },
          label: {
            textTransform: 'uppercase',
          },
        },
      },
      MuiOutlinedInput: {
        styleOverrides: {
          root: {
            '& .MuiOutlinedInput-notchedOutline': {
              borderColor: alpha(CYAN, 0.28),
            },
            '&:hover .MuiOutlinedInput-notchedOutline': {
              borderColor: alpha(CYAN, 0.5),
            },
            '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
              borderColor: CYAN,
              boxShadow: `0 0 8px ${alpha(CYAN, 0.25)}`,
            },
          },
        },
      },
      MuiInputLabel: {
        styleOverrides: {
          root: {
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            fontSize: '0.8rem',
          },
        },
      },
      MuiLinearProgress: {
        styleOverrides: {
          root: {
            height: 8,
            borderRadius: 2,
            backgroundColor: alpha(CYAN, 0.12),
            border: `1px solid ${alpha(CYAN, 0.2)}`,
          },
          bar: {
            borderRadius: 2,
            boxShadow: `0 0 10px ${alpha(CYAN, 0.7)}`,
          },
        },
      },
      MuiTableCell: {
        styleOverrides: {
          head: {
            color: CYAN,
            fontWeight: 700,
            borderBottom: `1px solid ${alpha(CYAN, 0.3)}`,
            backgroundColor: alpha(CYAN, 0.06),
          },
          root: {
            borderBottom: `1px solid ${alpha(CYAN, 0.12)}`,
          },
        },
      },
      MuiAlert: {
        styleOverrides: {
          root: {
            border: `1px solid ${alpha(CYAN, 0.2)}`,
            backgroundColor: alpha(BG_PAPER, 0.9),
          },
        },
      },
      MuiAccordion: {
        styleOverrides: {
          root: {
            backgroundImage: 'none',
            backgroundColor: alpha(BG_PAPER, 0.92),
            border: `1px solid ${alpha(CYAN, 0.22)}`,
            boxShadow: `0 0 14px ${alpha(CYAN, 0.06)}`,
            '&:before': {
              backgroundColor: alpha(CYAN, 0.2),
            },
            '&.Mui-expanded': {
              borderColor: alpha(CYAN, 0.45),
              boxShadow: `0 0 20px ${alpha(CYAN, 0.12)}`,
            },
          },
        },
      },
      MuiAccordionSummary: {
        styleOverrides: {
          expandIconWrapper: {
            color: CYAN,
          },
        },
      },
      MuiDialog: {
        styleOverrides: {
          paper: {
            backgroundColor: alpha(BG_PAPER, 0.98),
            border: `1px solid ${alpha(CYAN, 0.3)}`,
            boxShadow: `0 0 30px ${alpha(CYAN, 0.12)}`,
          },
        },
      },
      MuiDialogTitle: {
        styleOverrides: {
          root: {
            color: CYAN,
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            borderBottom: `1px solid ${alpha(CYAN, 0.22)}`,
          },
        },
      },
      MuiDialogActions: {
        styleOverrides: {
          root: {
            borderTop: `1px solid ${alpha(CYAN, 0.18)}`,
            padding: '16px 24px',
          },
        },
      },
      MuiSnackbarContent: {
        styleOverrides: {
          root: {
            backgroundColor: alpha(BG_PAPER, 0.98),
            border: `1px solid ${alpha(CYAN, 0.4)}`,
            boxShadow: `0 0 18px ${alpha(CYAN, 0.2)}`,
          },
        },
      },
    },
  });
}

export const appTheme = createAppTheme();
