import React, { useEffect, useState } from 'react';
import { SecureAPI } from '../lib/secureApi';

interface PropertyRow {
  id: string;
  tenant_id: string;
  name: string;
  timezone: string;
}

export const PropertiesList: React.FC = () => {
  const [properties, setProperties] = useState<PropertyRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    SecureAPI.getDashboardProperties()
      .then((res) => {
        if (active) setProperties(res.properties || []);
      })
      .catch((err) => {
        console.error(err);
        if (active) setError('Failed to load properties');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="p-4 lg:p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Properties</h1>
        <p className="text-sm text-gray-600 mt-1">Properties isolated to your organization</p>
      </div>

      {error && (
        <div role="alert" className="mb-4 p-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded-md">
          {error}
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50 text-left text-xs font-medium text-gray-600">
            <tr>
              <th className="px-5 py-3">Property ID</th>
              <th className="px-5 py-3">Name</th>
              <th className="px-5 py-3">Timezone</th>
              <th className="px-5 py-3">Tenant</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white">
            {loading ? (
              <tr>
                <td colSpan={4} className="px-5 py-6 text-center text-gray-500">
                  Loading properties...
                </td>
              </tr>
            ) : properties.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-5 py-6 text-center text-gray-500">
                  No properties found.
                </td>
              </tr>
            ) : (
              properties.map((p) => (
                <tr key={`${p.tenant_id}-${p.id}`} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-mono text-gray-800">{p.id}</td>
                  <td className="px-5 py-3 font-medium text-gray-900">{p.name}</td>
                  <td className="px-5 py-3 text-gray-600">{p.timezone}</td>
                  <td className="px-5 py-3 font-mono text-xs text-gray-500">{p.tenant_id}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default PropertiesList;
