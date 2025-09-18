from pydantic import BaseModel, ConfigDict


class PredictorRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "country": "Germany",
                "city": "Stuttgart",
                "num_invoices": 7,
                "total_spent": 37.62,
                "avg_invoice_total": 5.37,
                "tenure_days": 1721,
                "days_since_last_purchase": 432,
                "total_tracks": 38,
                "avg_price_per_track": 0.99,
                "unique_genres_bought": 7,
                "invoices_per_month": 0.1628,
                "top3_genres": "Rock (17), Blues (9), Latin (4)"
            }
        }
    )
    country: str
    city: str
    num_invoices: float
    total_spent: float
    avg_invoice_total: float
    tenure_days: float
    days_since_last_purchase: float
    total_tracks: float
    avg_price_per_track: float
    unique_genres_bought: float
    invoices_per_month: float
    top3_genres: str

