import type { CSSProperties } from 'react';
import { NavLink, Outlet } from 'react-router-dom';

import { navigationItems } from '../../router/navigation';

const shellStyle: CSSProperties = {
  minHeight: '100vh',
  display: 'grid',
  gridTemplateColumns: '280px minmax(0, 1fr)',
  background: '#eef3f8',
  color: '#162033'
};

const sidebarStyle: CSSProperties = {
  padding: '32px 20px',
  borderRight: '1px solid #d8e0ee',
  background: '#ffffff',
  display: 'grid',
  alignContent: 'start',
  gap: '24px'
};

const brandBlockStyle: CSSProperties = {
  display: 'grid',
  gap: '10px'
};

const brandStyle: CSSProperties = {
  margin: 0,
  fontSize: '24px',
  fontWeight: 800,
  letterSpacing: '-0.03em'
};

const brandMetaStyle: CSSProperties = {
  margin: 0,
  fontSize: '14px',
  lineHeight: 1.6,
  color: '#667085'
};

const navListStyle: CSSProperties = {
  listStyle: 'none',
  margin: 0,
  padding: 0,
  display: 'grid',
  gap: '14px'
};

const navItemStyle: CSSProperties = {
  display: 'grid',
  gap: '6px'
};

const navLinkBaseStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  width: 'fit-content',
  padding: '10px 14px',
  borderRadius: '12px',
  color: '#1f2937',
  fontWeight: 700,
  textDecoration: 'none'
};

const navLinkActiveStyle: CSSProperties = {
  background: '#2247a5',
  color: '#ffffff'
};

const navDescriptionStyle: CSSProperties = {
  margin: 0,
  paddingLeft: '2px',
  fontSize: '13px',
  lineHeight: 1.6,
  color: '#667085'
};

const contentStyle: CSSProperties = {
  padding: '32px',
  display: 'grid',
  alignContent: 'start'
};

export function AppShell() {
  return (
    <div style={shellStyle}>
      <aside style={sidebarStyle}>
        <div style={brandBlockStyle}>
          <p style={brandStyle}>WebToActions</p>
          <p style={brandMetaStyle}>
            阶段 1 先建立统一路由壳子、导航入口与测试基线。
          </p>
        </div>

        <nav aria-label="主导航">
          <ul style={navListStyle}>
            {navigationItems.map((item) => (
              <li key={item.to} style={navItemStyle}>
                <NavLink
                  to={item.to}
                  end={item.to === '/'}
                  style={({ isActive }) => ({
                    ...navLinkBaseStyle,
                    ...(isActive ? navLinkActiveStyle : {})
                  })}
                >
                  {item.label}
                </NavLink>
                <p style={navDescriptionStyle}>{item.description}</p>
              </li>
            ))}
          </ul>
        </nav>
      </aside>

      <main style={contentStyle}>
        <Outlet />
      </main>
    </div>
  );
}
