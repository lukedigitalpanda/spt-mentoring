import React from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../../utils/api';

interface SiteSettings {
  logo: string | null;
}

export default function BrandLogo({ size = 36 }: { size?: number }) {
  const { data } = useQuery<SiteSettings>({
    queryKey: ['site-settings'],
    queryFn: () => api.get('/cohorts/settings/').then(r => r.data),
    staleTime: Infinity,
  });

  if (!data?.logo) return null;

  return (
    <img
      src={data.logo}
      alt="Site logo"
      width={size}
      height={size}
      style={{ objectFit: 'contain' }}
    />
  );
}
