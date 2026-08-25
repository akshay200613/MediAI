/**
 * Vitest global setup.
 * Extends the Vitest `expect` with jest-dom matchers so tests can use
 * assertions like `toBeInTheDocument()`, `toHaveTextContent()`, etc.
 */
import '@testing-library/jest-dom'
