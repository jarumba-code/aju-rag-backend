"use client";

import { useState } from "react";
import { Users, Plus, Shield, Trash2 } from "lucide-react";

interface AdminUser {
  id: string;
  email: string;
  role: "admin" | "super_admin";
  lastLogin: string;
  status: "active" | "inactive";
}

const users: AdminUser[] = [
  { id: "1", email: "admin@aju.edu.ng", role: "super_admin", lastLogin: "2025-01-15 14:32", status: "active" },
  { id: "2", email: "support@aju.edu.ng", role: "admin", lastLogin: "2025-01-15 10:15", status: "active" },
  { id: "3", email: "content@aju.edu.ng", role: "admin", lastLogin: "2025-01-14 16:45", status: "inactive" },
];

export default function UsersPage() {
  const [showAddForm, setShowAddForm] = useState(false);

  return (
    <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-navy aju-serif">Admin Users</h1>
            <p className="text-sm text-slate-600 mt-1">Manage administrator accounts and permissions</p>
          </div>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-gold-600 text-white rounded-lg hover:bg-gold-700"
          >
            <Plus size={18} />
            Add Admin
          </button>
        </div>

        {showAddForm && (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-navy mb-4">Add New Administrator</h2>
            <form className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
                <input
                  type="email"
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gold-500"
                  placeholder="admin@example.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Role</label>
                <select className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gold-500">
                  <option value="admin">Admin</option>
                  <option value="super_admin">Super Admin</option>
                </select>
              </div>
              <div className="flex gap-3">
                <button type="submit" className="px-4 py-2 bg-gold-600 text-white rounded-lg hover:bg-gold-700">
                  Add User
                </button>
                <button
                  type="button"
                  onClick={() => setShowAddForm(false)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-50">
              <tr className="border-b border-slate-200">
                <th className="text-left py-3 px-6 text-sm font-semibold text-slate-700">Email</th>
                <th className="text-left py-3 px-6 text-sm font-semibold text-slate-700">Role</th>
                <th className="text-left py-3 px-6 text-sm font-semibold text-slate-700">Last Login</th>
                <th className="text-left py-3 px-6 text-sm font-semibold text-slate-700">Status</th>
                <th className="text-right py-3 px-6 text-sm font-semibold text-slate-700">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="border-b border-slate-100 hover:bg-slate-50">
                  <td className="py-4 px-6">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-gold-600 flex items-center justify-center">
                        <Shield className="text-white" size={16} />
                      </div>
                      <span className="font-medium text-slate-900">{user.email}</span>
                    </div>
                  </td>
                  <td className="py-4 px-6">
                    <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
                      user.role === "super_admin" ? "bg-purple-100 text-purple-800" : "bg-blue-100 text-blue-800"
                    }`}>
                      {user.role.replace("_", " ")}
                    </span>
                  </td>
                  <td className="py-4 px-6 text-sm text-slate-600">{user.lastLogin}</td>
                  <td className="py-4 px-6">
                    <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
                      user.status === "active" ? "bg-green-100 text-green-800" : "bg-slate-100 text-slate-800"
                    }`}>
                      {user.status}
                    </span>
                  </td>
                  <td className="py-4 px-6 text-right">
                    <button className="p-2 text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg">
                      <Trash2 size={18} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

  );
}
