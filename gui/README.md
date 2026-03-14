# Digital Archive Maker — Desktop App

Electron-based GUI wrapper for the `dam` CLI.

## Quick Start

1. Clone or download the repository
2. Install dependencies: `make install-deps`
3. Launch the GUI: `cd gui && npm start`

> **Note:** The GUI app runs from the repository and uses the existing Python environment and CLI tools.

## Development

For developers wanting to contribute:

### Prerequisites
- Node.js 18+ and npm (Python deps handled by `make install-deps`)

### Run in development
```bash
cd gui
npm install
npm start
```

### Create a desktop shortcut (macOS)
```bash
# Create an app bundle in /Applications
ln -s /path/to/your/repo/gui/src/main.js /Applications/Digital\ Archive\ Maker.app
# Or use Automator to create a double-clickable app that runs:
# cd /path/to/repo/gui && npm start
```
