import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'
import AppLayout from './layouts/AppLayout'
import Landing from './pages/Landing'
import Connect from './pages/Connect'

const Overview = lazy(() => import('./pages/Overview'))
const Clusters = lazy(() => import('./pages/Clusters'))
const Analytics = lazy(() => import('./pages/Analytics'))
const Content = lazy(() => import('./pages/Content'))
const Predictions = lazy(() => import('./pages/Predictions'))
const Insights = lazy(() => import('./pages/Insights'))
const Assistant = lazy(() => import('./pages/Assistant'))
const Privacy = lazy(() => import('./pages/Privacy'))

export default function App() {
  return (
    <Suspense fallback={<div className="min-h-screen" />}>
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/connect" element={<Connect />} />
      <Route path="/app" element={<AppLayout />}>
        <Route index element={<Overview />} />
        <Route path="clusters" element={<Clusters />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="content" element={<Content />} />
        <Route path="predictions" element={<Predictions />} />
        <Route path="insights" element={<Insights />} />
        <Route path="assistant" element={<Assistant />} />
        <Route path="privacy" element={<Privacy />} />
      </Route>
      <Route path="*" element={<Landing />} />
    </Routes>
    </Suspense>
  )
}
