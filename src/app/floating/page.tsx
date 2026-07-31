'use client'

import DesktopAgent from '@/components/DesktopAgent'

// Rendered inside the dedicated always-on-top frameless Electron window.
// ClientLayout skips the app chrome for this route, so the page is just コフ.
export default function FloatingPage() {
  return <DesktopAgent floating />
}
