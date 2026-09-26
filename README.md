# StockSense

StockSense is a responsive inventory operations dashboard for tracking stock across multiple warehouses. This first iteration is a frontend prototype built with React, TypeScript, Vite, Recharts, and Lucide icons.

## Run locally

Prerequisite: Node.js 20.19 or later, or Node.js 22.12 or later (required by Vite 8).

```sh
npm install
npm run dev
```

Vite prints the local URL when the development server starts. Run a production compile with `npm run build` and lint with `npm run lint`.

## Included workflows

- Registration, password login with OTP verification, forgot-password OTP, and sign-out
- Overview KPIs, stock movement chart, and reorder alerts
- Product search, category and warehouse filters, stock status filtering, and product details
- Receipt, delivery, transfer, and stock adjustment forms
- Transfer ledger entries for both source and destination
- Required adjustment reasons, movement history, and CSV export
- Receipt and transfer document workflow screens

## Prototype scope

The authentication screens are client-side demonstrations: no accounts or passwords are stored, OTPs are not sent, and any six-digit code advances the preview flow. User and inventory state reset on reload. Server-side authentication and authorization, durable storage, PostgreSQL migrations, email/SMS OTP delivery, and realtime updates are not connected yet. The dashboard and workflows are ready to be wired to the API and transactional stock ledger described in the product requirements.
