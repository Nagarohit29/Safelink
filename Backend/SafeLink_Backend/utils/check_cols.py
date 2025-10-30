import pandas as pd
from models.random_forest_trainer import RandomForestTrainer

df = pd.read_csv('data/All_Labelled.csv')
t = RandomForestTrainer()
t.load_model()

X = df.drop(columns=['Label'])
obj_cols = X.select_dtypes(include=['object']).columns.tolist()

print('Object columns:', obj_cols)
print('\nLabel encoders trained:', list(t.label_encoders.keys()))
print('\nChecking for actual string values...')

for col in obj_cols:
    unique_vals = X[col].dropna().unique()[:10]
    print(f'{col}: {len(unique_vals)} unique values - {unique_vals}')
