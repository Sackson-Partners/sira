import { Fragment, useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Dialog, Transition, Menu } from '@headlessui/react'
import {
  Bars3Icon,
  HomeIcon,
  BellAlertIcon,
  FolderIcon,
  TruckIcon,
  UsersIcon,
  Cog6ToothIcon,
  BellIcon,
  ArrowRightOnRectangleIcon,
  GlobeAltIcon,
  BuildingOffice2Icon,
  CubeIcon,
  ChartBarSquareIcon,
  DocumentTextIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'
import { useAuthStore } from '../stores/authStore'
import { wsService } from '../services/websocket'
import { notificationsApi } from '../services/api'
import AIChat from './AIChat'
import toast from 'react-hot-toast'

const navigation = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'Control Tower', href: '/control-tower', icon: GlobeAltIcon },
  { name: 'Shipments', href: '/shipments', icon: DocumentTextIcon },
  { name: 'Fleet & Assets', href: '/fleet', icon: TruckIcon },
  { name: 'Ports', href: '/ports', icon: BuildingOffice2Icon },
  { name: 'Market Intel', href: '/market', icon: ChartBarSquareIcon },
  { name: 'Alerts', href: '/alerts', icon: BellAlertIcon },
  { name: 'Cases', href: '/cases', icon: FolderIcon },
  { name: 'Movements', href: '/movements', icon: CubeIcon },
  { name: 'Users', href: '/users', icon: UsersIcon },
  { name: 'Settings', href: '/settings', icon: Cog6ToothIcon },
]

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ')
}

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [unreadCount, setUnreadCount] = useState(0)
  const [aiChatOpen, setAiChatOpen] = useState(false)
  const location = useLocation()
  const { user, logout } = useAuthStore()

  useEffect(() => {
    // Connect to WebSocket
    wsService.connect()

    // Fetch initial unread count
    notificationsApi.getUnreadCount().then((res) => {
      setUnreadCount(res.data.unread_count)
    })

    // Listen for notifications
    const unsubscribe = wsService.on('alert', (data) => {
      toast(
        <div>
          <strong className="font-semibold">{data.data.severity} Alert</strong>
          <p className="text-sm">{data.data.description?.slice(0, 100)}</p>
        </div>,
        {
          icon: '🚨',
          duration: 5000,
        }
      )
      setUnreadCount((prev) => prev + 1)
    })

    return () => {
      unsubscribe()
      wsService.disconnect()
    }
  }, [])

  return (
    <>
      <div>
        {/* Mobile sidebar */}
        <Transition.Root show={sidebarOpen} as={Fragment}>
          <Dialog as="div" className="relative z-50 lg:hidden" onClose={setSidebarOpen}>
            <Transition.Child
              as={Fragment}
              enter="transition-opacity ease-linear duration-300"
              enterFrom="opacity-0"
              enterTo="opacity-100"
              leave="transition-opacity ease-linear duration-300"
              leaveFrom="opacity-100"
              leaveTo="opacity-0"
            >
              <div className="fixed inset-0 bg-gray-900/80" />
            </Transition.Child>

            <div className="fixed inset-0 flex">
              <Transition.Child
                as={Fragment}
                enter="transition ease-in-out duration-300 transform"
                enterFrom="-translate-x-full"
                enterTo="translate-x-0"
                leave="transition ease-in-out duration-300 transform"
                leaveFrom="translate-x-0"
                leaveTo="-translate-x-full"
              >
                <Dialog.Panel className="relative mr-16 flex w-full max-w-xs flex-1">
                  <div className="flex grow flex-col gap-y-5 overflow-y-auto bg-primary-600 px-6 pb-4">
                    <div className="flex h-16 shrink-0 items-center">
                      <span className="text-2xl font-bold text-white">SIRA</span>
                    </div>
                    <nav className="flex flex-1 flex-col">
                      <ul className="flex flex-1 flex-col gap-y-7">
                        <li>
                          <ul className="-mx-2 space-y-1">
                            {navigation.map((item) => (
                              <li key={item.name}>
                                <Link
                                  to={item.href}
                                  className={classNames(
                                    location.pathname === item.href
                                      ? 'bg-primary-700 text-white'
                                      : 'text-primary-200 hover:text-white hover:bg-primary-700',
                                    'group flex gap-x-3 rounded-md p-2 text-sm leading-6 font-semibold'
                                  )}
                                >
                                  <item.icon className="h-6 w-6 shrink-0" aria-hidden="true" />
                                  {item.name}
                                </Link>
                              </li>
                            ))}
                          </ul>
                        </li>
                      </ul>
                    </nav>
                  </div>
                </Dialog.Panel>
              </Transition.Child>
            </div>
          </Dialog>
        </Transition.Root>

        {/* Desktop sidebar */}
        <div className="hidden lg:fixed lg:inset-y-0 lg:z-50 lg:flex lg:w-72 lg:flex-col">
          <div className="flex grow flex-col gap-y-5 overflow-y-auto bg-primary-600 px-6 pb-4">
            <div className="flex h-16 shrink-0 items-center">
              <span className="text-2xl font-bold text-white">SIRA</span>
              <span className="ml-2 text-sm text-primary-200">Platform</span>
            </div>
            <nav className="flex flex-1 flex-col">
              <ul className="flex flex-1 flex-col gap-y-7">
                <li>
                  <ul className="-mx-2 space-y-1">
                    {navigation.map((item) => (
                      <li key={item.name}>
                        <Link
                          to={item.href}
                          className={classNames(
                            location.pathname === item.href
                              ? 'bg-primary-700 text-white'
                              : 'text-primary-200 hover:text-white hover:bg-primary-700',
                            'group flex gap-x-3 rounded-md p-2 text-sm leading-6 font-semibold'
                          )}
                        >
                          <item.icon className="h-6 w-6 shrink-0" aria-hidden="true" />
                          {item.name}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </li>
                <li className="mt-auto">
                  <div className="text-xs text-primary-200">
                    Logged in as
                    <div className="font-semibold text-white">{user?.username}</div>
                    <div className="text-primary-300 capitalize">{user?.role}</div>
                  </div>
                </li>
              </ul>
            </nav>
          </div>
        </div>

        {/* Main content */}
        <div className="lg:pl-72">
          {/* Top bar */}
          <div className="sticky top-0 z-40 flex h-16 shrink-0 items-center gap-x-4 border-b border-gray-200 bg-white px-4 shadow-sm sm:gap-x-6 sm:px-6 lg:px-8">
            <button
              type="button"
              className="-m-2.5 p-2.5 text-gray-700 lg:hidden"
              onClick={() => setSidebarOpen(true)}
            >
              <span className="sr-only">Open sidebar</span>
              <Bars3Icon className="h-6 w-6" aria-hidden="true" />
            </button>

            <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
              <div className="flex flex-1"></div>
              <div className="flex items-center gap-x-4 lg:gap-x-6">
                {/* Notifications */}
                <button
                  type="button"
                  className="relative -m-2.5 p-2.5 text-gray-400 hover:text-gray-500"
                >
                  <span className="sr-only">View notifications</span>
                  <BellIcon className="h-6 w-6" aria-hidden="true" />
                  {unreadCount > 0 && (
                    <span className="absolute top-0 right-0 block h-4 w-4 rounded-full bg-danger-500 text-xs text-white text-center">
                      {unreadCount > 9 ? '9+' : unreadCount}
                    </span>
                  )}
                </button>

                {/* Separator */}
                <div className="hidden lg:block lg:h-6 lg:w-px lg:bg-gray-200" aria-hidden="true" />

                {/* Profile dropdown */}
                <Menu as="div" className="relative">
                  <Menu.Button className="-m-1.5 flex items-center p-1.5">
                    <span className="sr-only">Open user menu</span>
                    <span className="hidden lg:flex lg:items-center">
                      <span className="ml-4 text-sm font-semibold leading-6 text-gray-900">
                        {user?.username}
                      </span>
                    </span>
                  </Menu.Button>
                  <Transition
                    as={Fragment}
                    enter="transition ease-out duration-100"
                    enterFrom="transform opacity-0 scale-95"
                    enterTo="transform opacity-100 scale-100"
                    leave="transition ease-in duration-75"
                    leaveFrom="transform opacity-100 scale-100"
                    leaveTo="transform opacity-0 scale-95"
                  >
                    <Menu.Items className="absolute right-0 z-10 mt-2.5 w-32 origin-top-right rounded-md bg-white py-2 shadow-lg ring-1 ring-gray-900/5 focus:outline-none">
                      <Menu.Item>
                        {({ active }) => (
                          <button
                            onClick={logout}
                            className={classNames(
                              active ? 'bg-gray-50' : '',
                              'flex w-full items-center gap-x-2 px-3 py-1 text-sm leading-6 text-gray-900'
                            )}
                          >
                            <ArrowRightOnRectangleIcon className="h-5 w-5" />
                            Sign out
                          </button>
                        )}
                      </Menu.Item>
                    </Menu.Items>
                  </Transition>
                </Menu>
              </div>
            </div>
          </div>

          {/* Page content */}
          <main className="py-10">
            <div className="px-4 sm:px-6 lg:px-8">{children}</div>
          </main>
        </div>

        {/* AI Chat Button */}
        <button
          onClick={() => setAiChatOpen(!aiChatOpen)}
          className="fixed bottom-4 right-4 z-40 rounded-full bg-primary-600 p-3 text-white shadow-lg hover:bg-primary-700 transition-colors"
          title="SIRA AI Assistant"
        >
          <SparklesIcon className="h-6 w-6" />
        </button>

        {/* AI Chat Panel */}
        <AIChat isOpen={aiChatOpen} onClose={() => setAiChatOpen(false)} />
      </div>
    </>
  )
}
