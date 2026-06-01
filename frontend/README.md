# AI Resume Matcher Frontend

Modern React frontend for the AI Resume Matcher platform.

This application provides a complete UI for:

- Uploading resume and application form files
- Configuring LLM, embeddings, and retrieval parameters
- Running workflow sessions against the backend API
- Monitoring progress in real time
- Reviewing confidence-scored generated answers
- Sending targeted human feedback for refinement

## Sommaire

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Available Scripts](#available-scripts)
- [Backend Integration](#backend-integration)
- [Build And Deployment](#build-and-deployment)
- [Roadmap Notes](#roadmap-notes)

## Overview

The frontend is designed to make advanced RAG workflow operations accessible through a professional and practical interface.

Current UX capabilities:

- Dynamic configuration panel for runtime AI parameters
- Session lifecycle controls (create, upload, start, monitor)
- Result cards with confidence indicators and score context
- Field selection and human-in-the-loop feedback workflow
- Markdown rendering for richer generated responses

## Tech Stack

- React 18
- TypeScript-enabled components (`.tsx`) in feature modules
- Create React App (`react-scripts`) build tooling
- Tailwind CSS + PostCSS + Autoprefixer
- Lucide React icons
- React Markdown + `remark-gfm`
- Testing Library + Jest DOM

## Architecture

```text
src/
	app/                      # App-shell layer and composition entry points
	features/resume-matching/ # Feature-oriented module structure (in progress)
	components/               # Active UI component entry currently used by App.js
```

The project is in a transition from a monolithic UI file toward a modular feature-first structure.

## Project Structure

```text
frontend/
	public/                   # Static public assets
	src/
		app/                    # Application shell / module boundaries
		components/             # Main ResumeMatchingApp component used by App.js
		features/               # Modular feature domain (`resume-matching`)
		App.js                  # Root component mapping to ResumeMatchingApp
		index.js                # React bootstrap
	build/                    # Production output (generated)
	package.json              # Scripts and dependencies
	tailwind.config.js        # Tailwind configuration
	postcss.config.js         # PostCSS pipeline
```

## Prerequisites

- Node.js 18+ recommended
- npm 9+ recommended
- Running backend API service (default expected at `http://localhost:8000`)

## Quick Start

1. Install dependencies:

```bash
npm install
```

2. Start development server:

```bash
npm start
```

3. Open app in browser:

```text
http://localhost:3000
```

## Available Scripts

### `npm start`

Runs the frontend in development mode with hot reload.

### `npm run build`

Builds an optimized production bundle in `build/`.

### `npm test`

Runs tests in interactive watch mode.

### `npm run eject`

Exports CRA-managed configuration. Use only if you intentionally want full control of build internals.

## Backend Integration

Frontend currently targets backend base URL:

```text
http://localhost:8000
```

This value is currently defined in the UI code and should match your backend runtime host/port.

Typical backend interaction flow:

1. Create session
2. Upload resume + form
3. Start processing
4. Poll/stream status
5. Review generated fields
6. Submit feedback if needed
7. Retrieve final results

## Build And Deployment

Create production bundle:

```bash
npm run build
```

The generated `build/` directory can be deployed to any static host (Nginx, Vercel, Netlify, S3+CloudFront, etc.).

For production, ensure API endpoint configuration is aligned with the deployed backend URL.

## Roadmap Notes

- Centralize API configuration via environment variables
- Expand test coverage on feature and integration levels
- Introduce stronger state management boundaries where needed
