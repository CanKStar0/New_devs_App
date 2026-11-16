import React, { useEffect, useMemo, useState } from "react";
import { RevenueSummary } from "./RevenueSummary";
import { SecureAPI } from "../lib/secureApi";
import { useAuth } from "../contexts/AuthContext.new";

interface PropertyOption {
  id: string;
  name: string;
  tenant_id: string;
  timezone: string;
}

interface ReservationRow {
  id: string;
  property_id: string;
  property_name: string;
  timezone: string;
  check_in_date: string;
  check_in_local: string;
  check_out_date: string;
  total_amount: string;
  currency: string;
}

const PERIOD_OPTIONS = [
  { value: '2024-03', label: 'March 2024' },
  { value: '2024-02', label: 'February 2024' },
  { value: 'all', label: 'All Time' },
];

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const tenantId = (user as { tenant_id?: string } | null)?.tenant_id || 'tenant-a';

  const [properties, setProperties] = useState<PropertyOption[]>([]);
  const [selectedProperty, setSelectedProperty] = useState('prop-001');
  const [selectedPeriod, setSelectedPeriod] = useState('2024-03');
  const [reservations, setReservations] = useState<ReservationRow[]>([]);
  const [loadingRows, setLoadingRows] = useState(false);

  const parsedPeriod = useMemo(() => {
    if (selectedPeriod === 'all') {
      return { month: undefined, year: undefined };
    }
    const [yearStr, monthStr] = selectedPeriod.split('-');
    return { year: Number(yearStr), month: Number(monthStr) };
  }, [selectedPeriod]);

  useEffect(() => {
    let active = true;
    SecureAPI.getDashboardProperties()
      .then((res) => {
        if (!active) return;
        const list = res.properties || [];
        setProperties(list);
        if (list.length > 0 && !list.some((p) => p.id === selectedProperty)) {
          setSelectedProperty(list[0].id);
        }
      })
      .catch((err) => console.error('Failed to load properties:', err));
    return () => {
      active = false;
    };
  }, [tenantId]);

  useEffect(() => {
    let active = true;
    setLoadingRows(true);
    SecureAPI.getDashboardReservations({
      propertyId: selectedProperty,
      month: parsedPeriod.month,
      year: parsedPeriod.year,
    })
      .then((res) => {
        if (active) setReservations(res.reservations || []);
      })
      .catch((err) => console.error('Failed to load reservations:', err))
      .finally(() => {
        if (active) setLoadingRows(false);
      });
    return () => {
      active = false;
    };
  }, [selectedProperty, parsedPeriod]);

  const activeProp = properties.find((p) => p.id === selectedProperty);

  return (
    <div className="p-4 lg:p-6 min-h-full">
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Property Management Dashboard</h1>
            <p className="text-sm text-gray-600 mt-1">
              Workspace: <span className="font-mono font-medium text-gray-800">{tenantId}</span>
              {activeProp ? ` · ${activeProp.timezone}` : ''}
            </p>
          </div>
        </div>

        <section className="bg-white rounded-lg border border-gray-200 p-5 lg:p-6">
          <div className="mb-5 flex flex-col sm:flex-row sm:justify-between sm:items-end gap-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Revenue Overview</h2>
              <p className="text-sm text-gray-600 mt-1">
                Verified revenue totals in property-local timezone
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
              <div className="flex flex-col">
                <label htmlFor="period-select" className="text-xs font-medium text-gray-700 mb-1">
                  Period
                </label>
                <select
                  id="period-select"
                  value={selectedPeriod}
                  onChange={(e) => setSelectedPeriod(e.target.value)}
                  className="block w-full sm:w-auto min-w-[150px] px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  {PERIOD_OPTIONS.map((period) => (
                    <option key={period.value} value={period.value}>
                      {period.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex flex-col">
                <label htmlFor="property-select" className="text-xs font-medium text-gray-700 mb-1">
                  Property
                </label>
                <select
                  id="property-select"
                  value={selectedProperty}
                  onChange={(e) => setSelectedProperty(e.target.value)}
                  className="block w-full sm:w-auto min-w-[210px] px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  {properties.map((property) => (
                    <option key={`${property.tenant_id}-${property.id}`} value={property.id}>
                      {property.name} ({property.id})
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <RevenueSummary
            propertyId={selectedProperty}
            month={parsedPeriod.month}
            year={parsedPeriod.year}
          />
        </section>

        <section className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <h2 className="text-base font-semibold text-gray-900">Included Reservations</h2>
            <span className="text-xs text-gray-500 tabular-nums">{reservations.length} bookings</span>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50 text-left text-xs font-medium text-gray-600">
                <tr>
                  <th className="px-5 py-3">Reservation</th>
                  <th className="px-5 py-3">Check-in (Property Local)</th>
                  <th className="px-5 py-3">Check-in (UTC)</th>
                  <th className="px-5 py-3 text-right">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {loadingRows ? (
                  <tr>
                    <td colSpan={4} className="px-5 py-6 text-center text-gray-500">
                      Loading reservations...
                    </td>
                  </tr>
                ) : reservations.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-5 py-6 text-center text-gray-500">
                      No reservations found for this period.
                    </td>
                  </tr>
                ) : (
                  reservations.map((r) => (
                    <tr key={r.id} className="hover:bg-gray-50">
                      <td className="px-5 py-3 font-mono text-gray-800">{r.id}</td>
                      <td className="px-5 py-3 text-gray-800 tabular-nums">{r.check_in_local}</td>
                      <td className="px-5 py-3 text-gray-500 font-mono text-xs tabular-nums">
                        {r.check_in_date}
                      </td>
                      <td className="px-5 py-3 text-right font-medium text-gray-900 tabular-nums">
                        {r.currency} {r.total_amount}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
};

export default Dashboard;
