# PDF to Video Generator - Frontend

React frontend for the PDF to Video Generator application.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm start
```

The app will run on http://localhost:3000

**Note:** If you see a deprecation warning about `util._extend`, it's harmless and comes from a Node.js dependency. It doesn't affect functionality and can be safely ignored. This will be fixed in future dependency updates.

## Environment Variables

Create a `.env` file in the frontend directory:

```
REACT_APP_API_URL=http://localhost:8000
```

## Features

- Upload PDF files with drag-and-drop support
- Configure page range for video generation
- Real-time job status tracking
- Generate book summaries
- Generate summary videos
- Download generated videos and summaries

## Build for Production

```bash
npm run build
```

This creates an optimized production build in the `build` folder.

