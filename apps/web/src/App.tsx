/**
 * Main App Component
 * 
 * Root component that handles the main application view.
 * The ExperimentView component will automatically show the home page when no experiments exist.
 */

import { ExperimentView } from "@/components/experiment-view"

export default function App() {
  return <ExperimentView />
}
