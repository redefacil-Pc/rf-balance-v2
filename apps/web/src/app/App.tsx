import { RouterProvider } from 'react-router-dom';

import { AuthProvider } from '@/app/providers/AuthProvider';
import { QueryProvider } from '@/app/providers/QueryProvider';
import { UiProvider } from '@/app/providers/UiProvider';
import { router } from '@/app/router/router';

export function App() {
  return (
    <UiProvider>
      <QueryProvider>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </QueryProvider>
    </UiProvider>
  );
}
