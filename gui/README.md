# Digital Archive Maker — Desktop App

Electron-based GUI wrapper for the `dam` CLI.

## Download and Install

1. Go to [GitHub Releases](../../releases)
2. Download the latest `Digital-Archive-Maker-X.X.X.dmg`
3. Open the `.dmg` file
4. Drag the app to your Applications folder
5. Right-click the app and choose **Open** (first time only)

> **Gatekeeper note:** Since this is not notarized, users must right-click the app and choose **Open** the first time.

## Development

For developers wanting to contribute or run from source:

### Prerequisites
1. Python venv set up in the repo root:
   ```bash
   make install-deps
   source venv/bin/activate
   pip install -e .
   ```
2. Node.js 18+ and npm

### Run in development
```bash
cd gui
npm install
npm start
```
