import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './base.css'
import StockSense from './StockSense.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <StockSense />
  </StrictMode>,
)
