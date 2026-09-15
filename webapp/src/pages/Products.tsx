import { MarketplaceApi } from "../api/endpoints";
import { useApi } from "../hooks/useApi";
import { EmptyState, ErrorBanner, Spinner } from "../components/ui";

const CATEGORY_LABEL: Record<string, string> = {
  mobility: "Movilidad", monitoring: "Monitoreo", home_safety: "Seguridad en el hogar", daily_care: "Cuidado diario",
};

export default function Products() {
  const list = useApi(() => MarketplaceApi.products({}), []);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Artículos de apoyo</h1>
          <p>Catálogo de productos para facilitar el cuidado en el hogar.</p>
        </div>
      </div>
      {list.error && <ErrorBanner message={list.error} />}
      {list.loading && <Spinner />}
      {list.data && list.data.items.length === 0 && <EmptyState label="No hay artículos publicados." />}
      {list.data && list.data.items.length > 0 && (
        <div className="cg-grid">
          {list.data.items.map((p) => (
            <div key={p.product_id} className="cg-card">
              <div className="name">{p.name}</div>
              <div className="headline">{CATEGORY_LABEL[p.category] ?? p.category}</div>
              <div style={{ fontWeight: 700, color: "var(--ac-teal-700)" }}>{p.price_range}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
