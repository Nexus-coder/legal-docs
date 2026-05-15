"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function Sidebar() {
  const pathname = usePathname();

  const links = [
    { href: '/', icon: 'fa-columns', label: 'Dashboard' },
    { href: '/pii-masking', icon: 'fa-shield-alt', label: 'Context & PII' },
    { href: '/drafting', icon: 'fa-pen-nib', label: 'Drafting Workspace' },
  ];

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col h-screen overflow-hidden shrink-0">
      <div className="p-6 border-b border-slate-800">
        <h1 className="text-2xl font-bold text-white tracking-tight">
          <i className="fas fa-balance-scale mr-2"></i>LegalDocs
        </h1>
        <p className="text-xs text-slate-500 mt-1 uppercase tracking-widest">Legal-AI Suite</p>
      </div>
      <nav className="flex-1 p-4 space-y-2">
        {links.map((link) => {
          const isActive = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`w-full flex items-center px-4 py-3 rounded-lg hover:bg-slate-800 transition group ${
                isActive ? 'bg-slate-800 text-white' : ''
              }`}
            >
              <i className={`fas ${link.icon} mr-3 group-hover:text-blue-400 ${isActive ? 'text-blue-400' : 'text-slate-400'}`}></i> {link.label}
            </Link>
          );
        })}
        <div className="pt-6 border-t border-slate-800 mt-6">
          <Link
            href="/admin"
            className={`w-full flex items-center px-4 py-3 rounded-lg hover:bg-slate-800 transition group ${
              pathname === '/admin' ? 'bg-slate-800 text-white' : 'text-slate-400'
            }`}
          >
            <i className={`fas fa-user-shield mr-3 ${pathname === '/admin' ? 'text-blue-400' : ''}`}></i> Admin Console
          </Link>
        </div>
      </nav>
      <div className="p-4 border-t border-slate-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white font-bold">
              JD
            </div>
            <div className="text-xs">
              <p className="font-bold text-white">Advocate J. Doe</p>
              <p className="text-slate-500">Law Society ID: 4501</p>
            </div>
          </div>
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
