import '@testing-library/jest-dom/vitest'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

vi.mock('@google/model-viewer', () => ({}))

afterEach(() => {
  cleanup()
})

// jsdom does not implement the Notification API, but JobDetail checks it.
class NotificationStub {
  static permission: NotificationPermission = 'denied'
  static requestPermission = vi.fn(async (): Promise<NotificationPermission> => 'denied')
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  constructor(_title: string, _options?: NotificationOptions) {}
}

vi.stubGlobal('Notification', NotificationStub)
