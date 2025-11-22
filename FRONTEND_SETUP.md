# Frontend Setup Guide

This guide will help you set up and run the React frontend for the PDF to Video Generator.

## Prerequisites

- Node.js (v16 or higher)
- npm or yarn
- Backend API running on http://localhost:8000

## Installation

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

## Configuration

Create a `.env` file in the `frontend` directory (optional, defaults to localhost:8000):
```
REACT_APP_API_URL=http://localhost:8000
```

## Running the Application

1. Make sure the backend is running (see BACKEND_SETUP.md)

2. Start the React development server:
```bash
npm start
```

The frontend will open in your browser at http://localhost:3000

## Features

### 1. PDF Upload
- Drag and drop PDF files
- Select page range (start page and end page)
- Upload and start video generation

### 2. Job Status Tracking
- Real-time status updates
- Progress indicators
- Job metadata display
- Download main video when complete

### 3. Summary Generation
- Optional summary generation after main video
- Download summary text file
- Automatic prompt after main video completion

### 4. Summary Video Generation
- Optional summary video generation
- Uses the generated summary text
- Download summary video when complete

## Project Structure

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── PDFUpload.js          # PDF upload form
│   │   ├── JobStatus.js          # Job status tracking
│   │   ├── SummaryPrompt.js      # Summary generation prompt
│   │   └── SummaryVideoPrompt.js # Summary video generation prompt
│   ├── services/
│   │   └── api.js                # API service layer
│   ├── App.js                    # Main app component
│   ├── App.css                   # App styles
│   ├── index.js                  # Entry point
│   └── index.css                 # Global styles
├── package.json
└── README.md
```

## Building for Production

To create a production build:

```bash
npm run build
```

This creates an optimized build in the `build` folder that can be served by any static file server.

## Troubleshooting

### CORS Issues
If you encounter CORS errors, make sure:
1. The backend CORS middleware is configured correctly
2. The API URL in `.env` matches your backend URL

### API Connection Issues
- Verify the backend is running on the correct port
- Check the `REACT_APP_API_URL` environment variable
- Check browser console for detailed error messages

### Build Issues
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Clear npm cache: `npm cache clean --force`

