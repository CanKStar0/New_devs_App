import React, { useEffect, useState } from 'react';
import { SecureAPI } from '../lib/secureApi';

interface RevenueData {
  property_id: string;
  tenant_id?: string;
  total_revenue: number;
  total_revenue_exact?: string;
  currency: string;
  reservations_count: number;
}

interface RevenueSummaryProps {
  propertyId?: string;
  month?: number;
  year?: number;
  debugTenant?: string;
  showRaw?: boolean;
}

export const RevenueSummary: React.FC<RevenueSummaryProps> = ({
  propertyId = 'prop-001',
  month,
  year,
  debugTenant,
  showRaw,
}) => {
  const [data, setData] = useState<RevenueData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    const fetchRevenue = async () => {
      setLoading(true);
      setError('');
      try {
        const response = await SecureAPI.getDashboardSummary(propertyId, {
          ...(debugTenant ? { simulatedTenant: debugTenant } : {}),
          ...(month !== undefined && year !== undefined ? { month, year } : {}),
          timestamp: Date.now(),
        });
        if (active) setData(response);
      } catch (err) {
        console.error(err);
        if (active) setError('Failed to load revenue data');
      } finally {
        if (active) setLoading(false);
      }
    };

    fetchRevenue();
    return () => {
      active = false;
    };
  }, [propertyId, month, year, debugTenant]);

  if (loading) {
    return (
      <div className="py-6 animate-pulse space-y-4">
        <div className="h-4 bg-gray-100 rounded w-1/4" />
        <div className="h-8 bg-gray-100 rounded w-1/3" />
        <div className="flex gap-6 pt-4 border-t border-gray-100">
          <div className="h-10 bg-gray-100 rounded flex-1" />
          <div className="h-10 bg-gray-100 rounded flex-1" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div role="alert" className="p-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded-md">
        {error}
      </div>
    );
  }

  if (!data) return null;

  const exactNumeric = data.total_revenue_exact
    ? Number(data.total_revenue_exact)
    : Math.round(data.total_revenue * 100) / 100;

  return (
    <div className="pt-4 border-t border-gray-100">
      {showRaw && (
        <div className="mb-4 p-3 bg-gray-50 text-xs font-mono border border-gray-200 rounded-md overflow-auto max-h-32">
          <pre className="text-gray-700">{JSON.stringify(data, null, 2)}</pre>
        </div>
      )}

      <div className="mb-6">
        <p className="text-sm font-medium text-gray-600">Total Revenue</p>
        <p className="mt-1 text-3xl font-bold text-gray-900 tracking-tight tabular-nums">
          {data.currency}{' '}
          {exactNumeric.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-6 pt-4 border-t border-gray-100">
        <div>
          <p className="text-xs font-medium text-gray-500">Property ID</p>
          <p className="text-sm font-semibold text-gray-800 font-mono mt-1">{data.property_id}</p>
        </div>
        <div>
          <p className="text-xs font-medium text-gray-500">Reservations</p>
          <p className="text-sm font-semibold text-gray-800 mt-1 tabular-nums">
            {data.reservations_count}{' '}
            <span className="font-normal text-gray-500">bookings</span>
          </p>
        </div>
      </div>
    </div>
  );
};
