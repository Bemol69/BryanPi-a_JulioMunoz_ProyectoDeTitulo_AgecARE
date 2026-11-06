import { useEffect, useState } from "react";
import { MarketplaceApi } from "../api/endpoints";
import { useApi } from "../hooks/useApi";
import { EmptyState, ErrorBanner, Spinner } from "../components/ui";
import type { ProductCard, ProductCategory } from "../api/types";

const CATEGORIES: { key: ProductCategory | ""; label: string }[] = [
  { key: "", label: "Todos" },
  { key: "mobility", label: "Movilidad" },
  { key: "monitoring", label: "Monitoreo" },
  { key: "home_safety", label: "Seguridad en el hogar" },
  { key: "daily_care", label: "Cuidado diario" },
];
const CATEGORY_LABEL = Object.fromEntries(CATEGORIES.filter((c) => c.key).map((c) => [c.key, c.label])) as Record<string, string>;
const CATEGORY_ICON: Record<string, string> = { mobility: "🦯", monitoring: "❤️", home_safety: "🛁", daily_care: "💊" };

function ProductItem({ p }: { p: ProductCard }) {
  // El clic se cuenta sin frenar la navegación: el enlace abre la tienda en otra pestaña igual.
  function track() {
    MarketplaceApi.trackProductClick(p.product_id).catch(() => undefined);
  }
  return (
    <article className={`product-card${p.is_sponsored ? " sponsored" : ""}`}>
      <div className="product-media">
        {p.thumbnail_url
          ? <img src={p.thumbnail_url} alt="" loading="lazy" />
          : <span className={`product-ph ${p.category}`} aria-hidden>{CATEGORY_ICON[p.category] ?? "🛍️"}</span>}
        {p.is_sponsored && <span className="product-badge gold" title="Producto destacado por su proveedor">★ Destacado</span>}
      </div>
      <div className="product-body">
        {p.recommended_for && (
          <div className="product-reco" title="Según las condiciones registradas en el perfil">
            ✓ Recomendado para {p.recommended_for}
          </div>
        )}
        <div className="product-cat">{CATEGORY_LABEL[p.category] ?? p.category}{p.vendor && <> · {p.vendor}</>}</div>
        <h3 className="product-name">{p.name}</h3>
        {p.description && <p className="product-desc">{p.description}</p>}
        <div className="product-foot">
          <span className="product-price">{p.price_range}</span>
          {p.external_url ? (
            <a className="btn primary small" href={p.external_url} target="_blank" rel="noopener noreferrer sponsored" onClick={track}>
              Ver en tienda ↗
            </a>
          ) : (
            <span className="muted" style={{ fontSize: 12 }}>Consulta con el proveedor</span>
          )}
        </div>
      </div>
    </article>
  );
}

export default function Products() {
  const [category, setCategory] = useState<ProductCategory | "">("");
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");

  // Espera a que termine de escribir antes de consultar.
  useEffect(() => {
    const t = setTimeout(() => setSearch(query.trim()), 300);
    return () => clearTimeout(t);
  }, [query]);

  const list = useApi(() => MarketplaceApi.products({ category: category || undefined, q: search || undefined }), [category, search]);
  const items = list.data?.items ?? [];
  const recommended = items.filter((p) => p.recommended_for);
  const others = items.filter((p) => !p.recommended_for);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Artículos de apoyo</h1>
          <p>Productos de proveedores de confianza para que el cuidado en casa sea más seguro y cómodo.</p>
        </div>
      </div>

      <div className="product-toolbar">
        <input className="product-search" type="search" value={query} onChange={(e) => setQuery(e.target.value)}
              placeholder="Busca un producto o proveedor…" aria-label="Buscar artículos" />
        <div className="product-cats" role="tablist" aria-label="Categorías">
          {CATEGORIES.map((c) => (
            <button key={c.key || "all"} type="button" role="tab" aria-selected={category === c.key}
                    className={`product-cat-btn${category === c.key ? " on" : ""}`} onClick={() => setCategory(c.key)}>
              {c.label}
            </button>
          ))}
        </div>
      </div>

      {list.error && <ErrorBanner message={list.error} />}
      {list.loading && !list.data && <Spinner />}
      {list.data && items.length === 0 && <EmptyState label="No hay artículos que coincidan con tu búsqueda." />}

      {recommended.length > 0 && (
        <section className="product-section">
          <h2>Recomendados para tu familia</h2>
          <p className="product-section-sub">Según las condiciones que registraste en el perfil de tus adultos mayores.</p>
          <div className="product-grid">{recommended.map((p) => <ProductItem key={p.product_id} p={p} />)}</div>
        </section>
      )}
      {others.length > 0 && (
        <section className="product-section">
          {recommended.length > 0 && <h2>Todos los artículos</h2>}
          <div className="product-grid">{others.map((p) => <ProductItem key={p.product_id} p={p} />)}</div>
        </section>
      )}

      <p className="product-disclosure">
        AgeCare no vende estos productos: te lleva a la tienda del proveedor. Algunos enlaces son de referido, por lo que
        AgeCare puede recibir una comisión si compras, sin costo adicional para ti. Los productos marcados como «Destacado»
        están patrocinados por su proveedor.
      </p>
    </div>
  );
}
