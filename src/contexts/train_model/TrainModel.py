import numpy as np
import joblib
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv


from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, LabelEncoder
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression

class TrainModel:

    def entrenarModelo():

        #se usaron las credeciales para ingresar de manera ocacional (Transaction pooler)
        load_dotenv("/app/.env")
        USER = os.getenv("SUPABASE_USER")
        PASSWORD = os.getenv("SUPABASE_PASSWORD")
        HOST = os.getenv("SUPABASE_HOST")
        PORT = os.getenv("SUPABASE_PORT")
        DBNAME = os.getenv("SUPABASE_DBNAME")
        

        if(PORT== None):
            print("no se lee el env")
            return
        else:
            print("si se lee en env")


        try:
            with psycopg2.connect(
                user=USER,
                password=PASSWORD,
                host=HOST,
                port=PORT,
                dbname=DBNAME
            ) as connection:
                with connection.cursor() as cursor:
                    # Consulta SQL
                    cursor.execute('SELECT country, city, num_invoices, total_spent, avg_invoice_total, tenure_days, days_since_last_purchase, total_tracks, avg_price_per_track, unique_genres_bought, invoices_per_month, top3_genres, favorite_genre FROM "customer_ml_dataset";')
                    rows = cursor.fetchall()  # devuelve una lista de tuplas [(x1,y1),(x2,y2),...]
                    
                    print(f"Filas recuperadas: {len(rows)}")

        except Exception as e:
            print(f"Error al conectar o recuperar datos: {e}")
            return
        
        if not rows:
            print("No se recuperaron filas de la base de datos. Abortando entrenamiento.")
            return
        else:
            print(rows[:2])
            

        # Construir DataFrame con nombres de columnas
        columns = [
            "country",
            "city",
            "num_invoices",
            "total_spent",
            "avg_invoice_total",
            "tenure_days",
            "days_since_last_purchase",
            "total_tracks",
            "avg_price_per_track",
            "unique_genres_bought",
            "invoices_per_month",
            "top3_genres",
            "favorite_genre",
        ]
        df = pd.DataFrame(rows, columns=columns)

        # Separar variables de entrada (X) y objetivo (y)
        X = df.drop(columns=["favorite_genre"])  # 12 features
        y = df["favorite_genre"].astype(str)      # etiqueta categórica

        # Definir columnas categóricas y numéricas
        categorical_features = ["country", "city", "top3_genres"]
        numeric_features = [c for c in X.columns if c not in categorical_features]

        # Convertir columnas numéricas a float (pueden venir como Decimal/objeto)
        for column_name in numeric_features:
            X[column_name] = pd.to_numeric(X[column_name], errors="coerce")
        X[numeric_features] = X[numeric_features].fillna(0.0)

        # Preprocesamiento: OneHot para categóricas, passthrough para numéricas
        preprocessor = ColumnTransformer(
            transformers=[
                ("categorical", OneHotEncoder(handle_unknown="ignore"), categorical_features),
                ("numeric", "passthrough", numeric_features),
            ]
        )

        # Codificar y como etiquetas numéricas
        label_encoder = LabelEncoder()
        y_codes = label_encoder.fit_transform(y)

        # Dividir datos (evitar estratificación si hay clases con 1 muestra)
        class_counts = pd.Series(y_codes).value_counts()
        use_stratify = (class_counts.min() >= 2)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_codes, test_size=0.2, random_state=42,
            stratify=y_codes if use_stratify else None
        )

        # Modelo de clasificación multinomial
        classifier = LogisticRegression(max_iter=1000)

        # Pipeline completo
        pipeline = make_pipeline(preprocessor, classifier)
        pipeline.fit(X_train, y_train)

        # Guardar pipeline completo junto con el label encoder y columnas
        artifact = {
            "pipeline": pipeline,
            "label_encoder": label_encoder,
            "feature_columns": list(X.columns),
            "categorical_features": categorical_features,
            "numeric_features": numeric_features,
        }
        joblib.dump(artifact, str(os.getenv("MODELO_ENTRENADO")))
        print("modelo entrenado")
        
