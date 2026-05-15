"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  const links = [
    { href: '/', icon: 'fa-columns', label: 'Dashboard' },
    { href: '/pii-masking', icon: 'fa-shield-alt', label: 'Context & PII' },
    { href: '/drafting', icon: 'fa-pen-nib', label: 'Drafting Workspace' },
  ];

  useEffect(() => {
    setCollapsed(pathname.startsWith('/drafting'));
  }, [pathname]);

  return (
    <aside className={`${collapsed ? 'w-20' : 'w-64'} bg-slate-950 text-slate-300 flex flex-col h-screen overflow-hidden shrink-0 transition-[width] duration-300 ease-out`}>
      <div className={`${collapsed ? 'p-4' : 'p-5'} border-b border-slate-800`}>
        <div className={`flex items-center ${collapsed ? 'justify-center' : 'justify-between'} gap-3`}>
          <Link href="/" className="min-w-0 flex items-center gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white">
              <i className="fas fa-balance-scale"></i>
            </span>
            {!collapsed && (
              <span className="min-w-0">
                <span className="block text-lg font-bold tracking-tight text-white">LegalDocs</span>
                <span className="block text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">Legal-AI Suite</span>
              </span>
            )}
          </Link>
          {!collapsed && (
            <button
              onClick={() => setCollapsed(true)}
              className="h-8 w-8 rounded-md text-slate-500 transition hover:bg-slate-900 hover:text-white"
              title="Collapse navigation"
              aria-label="Collapse navigation"
            >
              <i className="fas fa-chevron-left text-xs"></i>
            </button>
          )}
        </div>
        {collapsed && (
          <button
            onClick={() => setCollapsed(false)}
            className="mt-4 h-9 w-full rounded-md text-slate-500 transition hover:bg-slate-900 hover:text-white"
            title="Expand navigation"
            aria-label="Expand navigation"
          >
            <i className="fas fa-chevron-right text-xs"></i>
          </button>
        )}
      </div>
      <nav className="flex-1 p-3 space-y-2">
        {links.map((link) => {
          const isActive = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              title={collapsed ? link.label : undefined}
              className={`w-full flex items-center ${collapsed ? 'justify-center px-0' : 'px-4'} py-3 rounded-lg hover:bg-slate-900 transition group ${
                isActive ? 'bg-slate-900 text-white ring-1 ring-slate-800' : ''
              }`}
            >
              <i className={`fas ${link.icon} ${collapsed ? '' : 'mr-3'} group-hover:text-blue-400 ${isActive ? 'text-blue-400' : 'text-slate-400'}`}></i>
              {!collapsed && <span className="truncate text-sm font-semibold">{link.label}</span>}
            </Link>
          );
        })}
        <div className="pt-6 border-t border-slate-800 mt-6">
          <Link
            href="/admin"
            title={collapsed ? 'Admin Console' : undefined}
            className={`w-full flex items-center ${collapsed ? 'justify-center px-0' : 'px-4'} py-3 rounded-lg hover:bg-slate-900 transition group ${
              pathname === '/admin' ? 'bg-slate-800 text-white' : 'text-slate-400'
            }`}
          >
            <i className={`fas fa-user-shield ${collapsed ? '' : 'mr-3'} ${pathname === '/admin' ? 'text-blue-400' : ''}`}></i>
            {!collapsed && <span className="truncate text-sm font-semibold">Admin Console</span>}
          </Link>
        </div>
      </nav>
      <div className="p-4 border-t border-slate-800">
        <div className={`flex items-center ${collapsed ? 'justify-center' : 'justify-between'}`}>
          {!collapsed && (
          <div className="flex min-w-0 items-center space-x-3">
            <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white font-bold">
              JD
            </div>
            <div className="min-w-0 text-xs">
              <p className="font-bold text-white">Advocate J. Doe</p>
              <p className="text-slate-500">Law Society ID: 4501</p>
            </div>
          </div>
          )}
          <button
            onClick={() => {
              document.cookie = "token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;";
              window.location.href = "/login";
            }}
            className="text-slate-500 hover:text-red-400 transition-colors p-2"
            title="Log Out"
          >
            <i className="fas fa-sign-out-alt"></i>
          </button>
        </div>
      </div>
    </aside>
  );
}
