/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useEffect } from 'react';

export default function App() {
  useEffect(() => {
    window.location.replace('/frontend/index.html');
  }, []);

  return (
    <div style={{ padding: '2rem', textAlign: 'center', fontFamily: 'system-ui, sans-serif' }}>
      Redirecting to <a href="/frontend/index.html">Smart Expense Tracker</a>...
    </div>
  );
}
