CREATE OR REPLACE VIEW customer_ml_dataset AS
WITH
-- 1) Agregados por factura (por cliente)
invoice_agg AS (
  SELECT
    c.customer_id,
    COUNT(DISTINCT i.invoice_id)                AS num_invoices,
    COALESCE(SUM(i.total), 0)::numeric(12,2)    AS total_spent,
    COALESCE(AVG(i.total), 0)::numeric(12,2)    AS avg_invoice_total,
    MIN(i.invoice_date)                         AS first_purchase_date,
    MAX(i.invoice_date)                         AS last_purchase_date
  FROM customer c
  LEFT JOIN invoice i ON i.customer_id = c.customer_id
  GROUP BY c.customer_id
),

-- 2) Agregados de líneas (tracks comprados, ticket por track)
line_agg AS (
  SELECT
    c.customer_id,
    COALESCE(SUM(il.quantity), 0)                               AS total_tracks,
    CASE
      WHEN COALESCE(SUM(il.quantity), 0) > 0
        THEN (SUM(il.unit_price * il.quantity) / SUM(il.quantity))::numeric(10,4)
      ELSE 0::numeric(10,4)
    END                                                         AS avg_price_per_track
  FROM customer c
  LEFT JOIN invoice i     ON i.customer_id = c.customer_id
  LEFT JOIN invoice_line il ON il.invoice_id = i.invoice_id
  GROUP BY c.customer_id
),

-- 3) Conteos/ingresos por género (para hallar el favorito y métricas de diversidad)
genre_counts AS (
  SELECT
    c.customer_id,
    g.name                                                       AS genre_name,
    COALESCE(SUM(il.quantity), 0)                                AS tracks_in_genre,
    COALESCE(SUM(il.unit_price * il.quantity), 0)::numeric(12,2) AS revenue_in_genre
  FROM customer c
  JOIN invoice i       ON i.customer_id = c.customer_id
  JOIN invoice_line il ON il.invoice_id = i.invoice_id
  JOIN track t         ON t.track_id = il.track_id
  JOIN genre g         ON g.genre_id = t.genre_id
  GROUP BY c.customer_id, g.name
),

-- 4) Género favorito por cliente (desempate por revenue y por nombre)
favorite_genre AS (
  SELECT customer_id, genre_name, tracks_in_genre, revenue_in_genre, rn
  FROM (
    SELECT
      gc.*,
      ROW_NUMBER() OVER (
        PARTITION BY gc.customer_id
        ORDER BY gc.tracks_in_genre DESC, gc.revenue_in_genre DESC, gc.genre_name ASC
      ) AS rn
    FROM genre_counts gc
  ) x
  WHERE rn = 1
),

-- 5) Top-3 géneros como texto (útil para EDA)
top3_genres AS (
  SELECT customer_id,
         STRING_AGG(genre_name || ' (' || tracks_in_genre::text || ')', ', ' ORDER BY tracks_in_genre DESC, revenue_in_genre DESC, genre_name ASC)
           FILTER (WHERE rn <= 3) AS top3_genres
  FROM (
    SELECT
      gc.*,
      ROW_NUMBER() OVER (
        PARTITION BY gc.customer_id
        ORDER BY gc.tracks_in_genre DESC, gc.revenue_in_genre DESC, gc.genre_name ASC
      ) AS rn
    FROM genre_counts gc
  ) r
  GROUP BY customer_id
),

-- 6) Métricas de diversidad de géneros
genre_diversity AS (
  SELECT
    customer_id,
    COUNT(*)                     AS unique_genres_bought,
    COALESCE(SUM(tracks_in_genre), 0) AS tracks_total_check
  FROM genre_counts
  GROUP BY customer_id
)

-- 7) Ensamble final: features (X) + target (Y)
SELECT
  c.customer_id,
  (c.first_name || ' ' || c.last_name)           AS customer_name,
  c.country,
  c.city,
  c.support_rep_id,

  ia.num_invoices,
  ia.total_spent,
  ia.avg_invoice_total,
  ia.first_purchase_date,
  ia.last_purchase_date,

  -- Tenure y recencia (en días)
  CASE WHEN ia.first_purchase_date IS NOT NULL
       THEN (CURRENT_DATE - ia.first_purchase_date::date)
       ELSE NULL END                              AS tenure_days,
  CASE WHEN ia.last_purchase_date IS NOT NULL
       THEN (CURRENT_DATE - ia.last_purchase_date::date)
       ELSE NULL END                              AS days_since_last_purchase,

  la.total_tracks,
  la.avg_price_per_track,

  gd.unique_genres_bought,
  t3.top3_genres,

  -- Frecuencia de compra por mes (aprox) durante el periodo activo
  CASE
    WHEN ia.first_purchase_date IS NOT NULL AND ia.last_purchase_date IS NOT NULL
    THEN
      ia.num_invoices::numeric
      /
      GREATEST(
        1,
        (
          (EXTRACT(YEAR  FROM ia.last_purchase_date) * 12 + EXTRACT(MONTH FROM ia.last_purchase_date))
          -
          (EXTRACT(YEAR  FROM ia.first_purchase_date) * 12 + EXTRACT(MONTH FROM ia.first_purchase_date))
          + 1
        )
      )
    ELSE NULL
  END::numeric(10,4)                               AS invoices_per_month,

  -- ======= TARGET (Y): género favorito =======
  fg.genre_name                                    AS favorite_genre,         -- <- Y
  fg.tracks_in_genre                               AS favorite_genre_tracks,  -- apoyo
  fg.revenue_in_genre                              AS favorite_genre_revenue   -- apoyo

FROM customer c
LEFT JOIN invoice_agg   ia ON ia.customer_id = c.customer_id
LEFT JOIN line_agg      la ON la.customer_id = c.customer_id
LEFT JOIN genre_diversity gd ON gd.customer_id = c.customer_id
LEFT JOIN top3_genres   t3 ON t3.customer_id = c.customer_id
LEFT JOIN favorite_genre fg ON fg.customer_id = c.customer_id;


SELECT * FROM customer_ml_dataset limit 1