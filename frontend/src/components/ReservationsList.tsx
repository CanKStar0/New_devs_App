import React, { useEffect, useState } from 'react';
import { SecureAPI } from '../lib/secureApi';

interface ReservationItem {
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

export const ReservationsList: React.FC = () => {
  const [reservations, setReservations] = useState<ReservationItem[]>([]);
  const [totalExact, setTotalExact] = useState('0.00');
  const [period, setPeriod] = useState('2024-03');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    const [y, m] = period === 'all' ? [undefined, undefined] : period.split('-').map(Number);

    SecureAPI.getDashboardReservations({ month: m, year: y })
      .then((res) => {
        if (!active) return;
        setReservations(res.reservations || []);
        setTotalExact(res.total_revenue_exact || '0.00');
      })
      .catch((err) => console.error(err))
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [period]);

  return (
    <div className="p-4 lg:p-6 max-w-5xl mx-auto">
      <div className="mb-6 flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reservations</h1>
          <p className="text-sm text-gray-600 mt-1">
            Total for period:{' '}
            <span className="font-semibold text-gray-900 tabular-nums">USD {totalExact}</span>
          </p>
        </div>

        <div className="flex flex-col">
          <label htmlFor="res-period" className="text-xs font-medium text-gray-700 mb-1">
            Period
          </label>
          <select
            id="res-period"
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="2024-03">March 2024</option>
            <option value="2024-02">February 2024</option>
            <option value="all">All Time</option>
          </select>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50 text-left text-xs font-medium text-gray-600">
              <tr>
                <th className="px-5 py-3">ID</th>
                <th className="px-5 py-3">Property</th>
                <th className="px-5 py-3">Check-in (Local)</th>
                <th className="px-5 py-3">Check-in (UTC)</th>
                <th className="px-5 py-3 text-right">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-5 py-6 text-center text-gray-500">
                    Loading reservations...
                  </td>
                </tr>
              ) : reservations.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-5 py-6 text-center text-gray-500">
                    No reservations found.
                  </td>
                </tr>
              ) : (
                reservations.map((r) => (
                  <tr key={r.id} className="hover:bg-gray-50">
                    <td className="px-5 py-3 font-mono text-gray-800">{r.id}</td>
                    <td className="px-5 py-3 text-gray-900">
                      {r.property_name}{' '}
                      <span className="text-xs text-gray-500 font-mono">({r.property_id})</span>
                    </td>
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
      </div>
    </div>
  );
};

export default ReservationsList;
