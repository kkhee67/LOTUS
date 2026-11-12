import React from 'react';
import {createRoot} from 'react-dom/client';
import {ProfileForm} from './features/profile/ProfileForm';
import './styles.css';

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ProfileForm />
  </React.StrictMode>,
);
