# Network Scanner Frontend

React + TypeScript + Vite frontend for the Network Scanner application.

## Features

- 🎨 Modern UI with Material-UI components
- 🔄 Real-time scan progress via WebSocket
- 📊 Network topology visualization
- 📈 Scan results with filtering and export
- ⏰ Scheduled scan management
- 🌙 Dark mode theme

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Material-UI** - Component library
- **Zustand** - State management
- **React Router** - Routing
- **Axios** - HTTP client
- **D3.js** - Network visualization
- **TanStack Table** - Data tables
- **React Hook Form + Zod** - Form validation

## Getting Started

### Docker (Recommended)

See main [Docker Documentation](../docs/DOCKER.md) for complete instructions.

Quick start:
```bash
# From project root
docker-compose up -d frontend
```

### Local Development

#### Prerequisites

- Node.js 18+ and npm

### Installation

1. Install dependencies:
```bash
npm install
```

2. Configure environment:
```bash
copy .env.example .env
```

3. Start development server:
```bash
npm run dev
```

The application will be available at `http://localhost:5173`

## Project Structure

```
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── Dashboard/       # Main dashboard
│   │   ├── ScanConfig/      # Scan configuration form
│   │   ├── ScanProgress/    # Real-time progress display
│   │   ├── NetworkTopology/ # Network graph visualization
│   │   ├── ResultsTable/    # Scan results table
│   │   └── ScheduleManager/ # Schedule management
│   ├── hooks/               # Custom React hooks
│   ├── services/            # API clients
│   │   ├── api.ts           # REST API client
│   │   └── websocket.ts     # WebSocket client
│   ├── store/               # Zustand state management
│   ├── types/               # TypeScript types
│   ├── utils/               # Utility functions
│   ├── App.tsx              # Main app component
│   └── main.tsx             # Entry point
├── public/                  # Static assets
├── index.html               # HTML template
├── vite.config.ts           # Vite configuration
├── tsconfig.json            # TypeScript configuration
└── package.json             # Dependencies
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run test` - Run tests

## Development

### Adding New Components

Components are organized by feature in the `src/components` directory. Each major feature has its own folder.

### State Management

Global state is managed with Zustand in `src/store/scanStore.ts`. Local component state uses React hooks.

### API Integration

- REST API calls: Use `src/services/api.ts`
- WebSocket: Use `src/services/websocket.ts`

### Styling

The application uses Material-UI with a custom dark theme defined in `src/main.tsx`.

## Building for Production

```bash
npm run build
```

The build output will be in the `dist/` directory.

## Integration with Backend

The frontend expects the backend API to be running on `http://localhost:8000`. This is configured in `.env` and proxied through Vite during development.

## Next Steps

To complete the frontend implementation:

1. Implement ScanConfig form component
2. Add NetworkTopology visualization with D3.js
3. Create ResultsTable with TanStack Table
4. Build ScheduleManager interface
5. Add export functionality
6. Implement authentication (if needed)
7. Add comprehensive error handling
8. Write unit tests with Vitest

## License

This project is for educational and authorized network scanning purposes only.
