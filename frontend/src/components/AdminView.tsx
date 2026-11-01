import { useState } from "react";
import { Link } from "react-router-dom";

import type { Category } from "../types";
import AdminPrompts from "./admin/AdminPrompts";
import AdminResponses from "./admin/AdminResponses";
import AdminUsers from "./admin/AdminUsers";

const TABS = [
  { id: "users", label: "Usuaris" },
  { id: "prompts", label: "Prompts" },
  { id: "responses", label: "Inferències" },
] as const;

type Tab = (typeof TABS)[number]["id"];

export default function AdminView({
  email,
  categories,
}: {
  email: string | null;
  categories: Category[];
}) {
  const [tab, setTab] = useState<Tab>("users");

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-8">
      <Link to="/" className="text-sm text-brand-600 hover:underline">
        Torna a l'inici
      </Link>
      <h1 className="text-2xl font-bold">Administració</h1>
      <div
        role="tablist"
        aria-label="Seccions d'administració"
        className="flex gap-2 border-b border-slate-200"
      >
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={tab === item.id}
            onClick={() => setTab(item.id)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
              tab === item.id
                ? "border-brand-500 text-brand-700"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div role="tabpanel">
        {tab === "users" && <AdminUsers selfEmail={email} />}
        {tab === "prompts" && <AdminPrompts categories={categories} />}
        {tab === "responses" && <AdminResponses />}
      </div>
    </div>
  );
}
