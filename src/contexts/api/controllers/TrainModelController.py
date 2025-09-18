import os
import joblib
import numpy as np
import os
import pandas as pd

from src.contexts.api.models import PredictorRequest



class TrainModelController:
    def execute(self, request: PredictorRequest):
        print(request)
        # Extraer datos del request
        row = {
            "country": request.country,
            "city": request.city,
            "num_invoices": request.num_invoices,
            "total_spent": request.total_spent,
            "avg_invoice_total": request.avg_invoice_total,
            "tenure_days": request.tenure_days,
            "days_since_last_purchase": request.days_since_last_purchase,
            "total_tracks": request.total_tracks,
            "avg_price_per_track": request.avg_price_per_track,
            "unique_genres_bought": request.unique_genres_bought,
            "invoices_per_month": request.invoices_per_month,
            "top3_genres": request.top3_genres,
        }

        artifact_path = os.getenv("MODELO_ENTRENADO")
        artifact = joblib.load(artifact_path)

        pipeline = artifact["pipeline"]
        label_encoder = artifact["label_encoder"]
        feature_columns = artifact["feature_columns"]

        # Construir DataFrame con el mismo orden de columnas que en entrenamiento
        X_df = pd.DataFrame([row]).reindex(columns=feature_columns)

        # Predecir y decodificar etiqueta
        y_code = pipeline.predict(X_df)[0]
        y_label = label_encoder.inverse_transform([int(y_code)])[0]

        return {"status": "OK", "result": y_label}

    
