# Product Requirements Document (PRD)

## Project Name: SigmaLite

### Executive Summary

SigmaLite is a collaborative, web-based data exploration and visualization platform inspired by Sigma Computing's mission to democratize analytics. It allows users to upload datasets, analyze data using spreadsheet-like interactions, and visualize results through intuitive dashboards — all within a browser.

The goal of SigmaLite is to bridge the simplicity of spreadsheets with the power of modern data systems, enabling users to derive insights interactively without writing complex code.

---

## 1. Objectives

| Objective | Description |
| ---------------------------------- | -------------------------------------------------------------------------------------------------- |
| **Empower data exploration** | Allow users to interact with structured data (e.g., CSV, API) using spreadsheet-style features. |
| **Enable real-time collaboration** | Support multiple users editing or viewing data simultaneously. |
| **Simplify data visualization** | Provide easy tools to create charts, dashboards, and summaries without coding. |
| **Demonstrate engineering depth** | Showcase scalable full-stack design with efficient data handling and secure multi-user operations. |
| **Show product thinking** | Balance UX simplicity with backend performance and security — mirroring Sigma's product goals. |

---

## 2. Key Features

### 4.1 Spreadsheet Data Interface

- Upload CSV or connect to public API (e.g., JSON dataset)
- Spreadsheet-like grid (editable cells, sortable columns)
- Auto-type detection (numeric, text, date)
- Basic formula support (e.g., SUM(A1:A5), AVG(B:B))

### 4.2 Data Visualization

- Interactive charts (line, bar, scatter, pie)
- Drag-and-drop chart builder
- Real-time updates when data changes
- Download/export chart as image or PDF

### 4.3 Real-Time Collaboration

- Multi-user editing with live cursors
- Commenting and "View-only" sharing
- Real-time updates via WebSockets

### 4.4 User Authentication & Persistence

- Secure login (JWT)
- Each user has their own workspace
- Save, rename, and reopen sheets and dashboards

### 4.5 Backend & Query Engine

- REST API for CRUD operations on datasets
- Basic query endpoints: `/filter`, `/aggregate`, `/visualize`
- Pagination and caching for large datasets
- Data validation and error handling

### 4.6 Performance & Security

- Input sanitization and rate limiting
- Backend caching layer (Redis)
- Efficient client-side rendering with virtualization for large tables

---

## 3. Architecture

### System Overview

```
[Frontend (React + TypeScript)]
        ↓
[Backend API (FastAPI)]
        ↓
[Database (PostgreSQL)]
        ↕
[Cache (Redis, optional)]
        ↓
[Cloud Hosting (Render / Vercel)]
```

| Component | Purpose |
| ------------------------------- | ------------------------------------------------ |
| **Frontend (React)** | UI rendering, charting, spreadsheet interactions |
| **Backend (FastAPI)** | Data processing, user management, analytics API |
| **Database (PostgreSQL)** | Store datasets, user info, sheet metadata |
| **WebSocket** | Real-time sync and collaboration |
| **Charting Library** | Chart.js for interactive visualizations |

---

## 4. Functional Requirements

| ID | Feature | Description | Priority |
| ----- | ------------------- | -------------------------------------------- | -------- |
| FR-1 | Data Upload | Users can upload CSV files (≤ 10MB) | High |
| FR-2 | Grid Rendering | Display dataset in editable spreadsheet grid | High |
| FR-3 | Sorting & Filtering | Allow column sorting and filtering | High |
| FR-4 | Chart Creation | Users can create charts from selected data | High |
| FR-5 | Save & Load | Save projects to user account | Medium |
| FR-6 | Collaboration | Allow multiple users to edit simultaneously | Medium |
| FR-7 | Comments | Allow inline comments | Low |
| FR-8 | Auth System | Login/signup with JWT | High |
| FR-9 | API Queries | `/filter`, `/aggregate`, `/chart` endpoints | Medium |
| FR-10 | Export | Export chart or table to CSV or image | Medium |

---

## 5. Non-Functional Requirements

| Category | Requirement |
| ------------------- | ------------------------------------------------ |
| **Performance** | Load initial grid under 2 seconds for < 10K rows |
| **Security** | Authentication and sanitized API endpoints |
| **Scalability** | Support 10+ concurrent users in one workspace |
| **Reliability** | 99% uptime (mocked locally) |
| **Usability** | Simple and responsive UI on desktop browsers |
| **Maintainability** | Modular codebase, TypeScript typing, unit tests |

---

## 6. Technical Stack

| Layer | Technology |
| ------------------- | ------------------------------------- |
| **Frontend** | React + TypeScript, Tailwind CSS |
| **Visualization** | Chart.js |
| **Backend** | FastAPI (Python) |
| **Database** | PostgreSQL |
| **Realtime Sync** | WebSockets |
| **Auth** | JWT |
| **Hosting** | Render (backend), Vercel (frontend) |
| **Version Control** | GitHub |
| **Testing** | Vitest (frontend), PyTest (backend) |

---

## 7. User Flows

### Example: Data Upload & Visualization

1. User logs in.
2. Uploads CSV → backend parses and returns schema.
3. Spreadsheet renders with data preview.
4. User selects columns → clicks "Visualize."
5. Chooses chart type → chart updates dynamically.
6. User saves dashboard → persists in DB.

### Example: Collaboration Flow

1. Two users open same sheet.
2. Edits are synced in real time via WebSocket.
3. Both see changes instantly.

---

## 8. Success Metrics

| Metric | Target |
| --------------------------------------- | ------ |
| App loads dataset < 2s for 10K rows | ✅ |
| Chart renders dynamically < 500ms | ✅ |
| No major security vulnerabilities | ✅ |
| At least 80% test coverage (core logic) | ✅ |
| Usability rating > 8/10 (peer review) | ✅ |

---

## 9. Deliverables

- ✅ Deployed app (e.g., sigmalite.vercel.app)
- ✅ Public GitHub repo with:
  - PRD & README
  - Architecture diagram
  - Screenshots / Demo GIF
  - Setup instructions
  - Unit tests & CI pipeline

---

## 10. Summary

SigmaLite demonstrates an engineer's ability to:

- Build production-quality, full-stack systems
- Translate business needs into technical features
- Balance scalability, security, and user experience
- Take ownership from ideation → deployment

This project aligns perfectly with modern data platform expectations and shows initiative, curiosity, and technical competence.
