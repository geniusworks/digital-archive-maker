# Digital Archive Maker — Desktop App

Electron-based GUI wrapper for the `dam` CLI.

## Prerequisites

1. Python venv set up in the repo root:
   ```bash
   make install-deps
   source venv/bin/activate
   pip install -e .
   ```
2. Node.js 18+ and npm

## Run in development

```bash
cd gui
npm install
npm start
```

## Build a distributable .dmg

```bash
cd gui
npm install
npm run build:dmg
```

The `.dmg` will be in `gui/dist/`. Distribute via GitHub Releases.

> **Gatekeeper note:** Since this is not notarized, users must right-click the app and choose **Open** the first time.

## Adding the app icon

Place a 1024×1024 `.icns` (macOS) and `.png` file in `gui/assets/`:
- `gui/assets/icon.icns`
- `gui/assets/icon.png`

Use `electron-icon-builder` or any `.icns` generator from a square PNG.
