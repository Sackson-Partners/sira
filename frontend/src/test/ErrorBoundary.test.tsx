import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ErrorBoundary from '../components/ErrorBoundary'

// Component that always throws during render
const ThrowingComponent = ({ message = 'Test error' }: { message?: string }) => {
  throw new Error(message)
}

// Normal child component
const NormalComponent = () => <div data-testid="normal-child">Hello</div>

// Suppress React's error boundary console.error output in tests
const originalConsoleError = console.error
beforeEach(() => {
  console.error = vi.fn()
})
afterEach(() => {
  console.error = originalConsoleError
})

describe('ErrorBoundary', () => {
  describe('normal render path', () => {
    it('renders children when no error occurs', () => {
      render(
        <ErrorBoundary>
          <NormalComponent />
        </ErrorBoundary>
      )
      expect(screen.getByTestId('normal-child')).toBeTruthy()
      expect(screen.getByText('Hello')).toBeTruthy()
    })

    it('renders multiple children without issue', () => {
      render(
        <ErrorBoundary>
          <div data-testid="child-1">First</div>
          <div data-testid="child-2">Second</div>
        </ErrorBoundary>
      )
      expect(screen.getByTestId('child-1')).toBeTruthy()
      expect(screen.getByTestId('child-2')).toBeTruthy()
    })
  })

  describe('error handling', () => {
    it('renders error UI when a child throws', () => {
      render(
        <ErrorBoundary>
          <ThrowingComponent />
        </ErrorBoundary>
      )
      expect(screen.getByText(/something went wrong/i)).toBeTruthy()
    })

    it('displays the error message in the fallback UI', () => {
      render(
        <ErrorBoundary>
          <ThrowingComponent message="Custom error message" />
        </ErrorBoundary>
      )
      expect(screen.getByText(/custom error message/i)).toBeTruthy()
    })

    it('shows a "Go to Login" button in the error UI', () => {
      render(
        <ErrorBoundary>
          <ThrowingComponent />
        </ErrorBoundary>
      )
      const button = screen.getByRole('button', { name: /go to login/i })
      expect(button).toBeTruthy()
    })

    it('calls componentDidCatch with the error and info', () => {
      const spy = vi.spyOn(ErrorBoundary.prototype, 'componentDidCatch')
      render(
        <ErrorBoundary>
          <ThrowingComponent message="caught error" />
        </ErrorBoundary>
      )
      expect(spy).toHaveBeenCalled()
      const [caughtError] = spy.mock.calls[0]
      expect((caughtError as Error).message).toBe('caught error')
      spy.mockRestore()
    })

    it('getDerivedStateFromError sets hasError=true', () => {
      const error = new Error('state error')
      const state = ErrorBoundary.getDerivedStateFromError(error)
      expect(state.hasError).toBe(true)
      expect(state.error).toBe(error)
    })
  })

  describe('recovery', () => {
    it('"Go to Login" button resets state', () => {
      // Mock window.location.href assignment
      const originalHref = window.location.href
      Object.defineProperty(window, 'location', {
        value: { href: originalHref },
        writable: true,
      })

      render(
        <ErrorBoundary>
          <ThrowingComponent />
        </ErrorBoundary>
      )

      const button = screen.getByRole('button', { name: /go to login/i })
      fireEvent.click(button)

      // After clicking, location should be /login
      expect(window.location.href).toBe('/login')
    })
  })
})
