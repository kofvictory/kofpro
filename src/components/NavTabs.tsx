'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const tabs = [
  { href: '/triage', label: 'Inbox' },
  { href: '/active', label: '着手中' },
  { href: '/today',  label: '今日' },
]

export default function NavTabs() {
  const pathname = usePathname()
  return (
    <nav className="flex gap-1">
      {tabs.map(tab => (
        <Link
          key={tab.href}
          href={tab.href}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            pathname === tab.href
              ? 'bg-blue-600 text-white'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          {tab.label}
        </Link>
      ))}
    </nav>
  )
}
