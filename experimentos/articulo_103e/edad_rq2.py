"""RQ2: desempeño según la edad (3-4, 5 y 6 años) de Random Forest y EfficientNet-B0, con las predicciones fuera
de pliegue. Exactitud balanceada con IC 95 % (bootstrap por niño, 2000 réplicas, semilla 20261024), error medio y
sesgo de la PD. El niño sin edad queda fuera."""
import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score as ba

p = pd.read_csv("participantes_103.csv")[["child_id", "edad_anios"]]
for nombre, archivo in [("Random Forest", "oof_crit_con_criterios_sin_proporcion_random_forest"),
                        ("EfficientNet-B0", "oof_dl_efficientnet_b0_corte")]:
    o = pd.read_parquet(f"processed/{archivo}.parquet").merge(p, on="child_id")
    o["grupo"] = o.edad_anios.map({3: "3-4", 4: "3-4", 5: "5", 6: "6"})
    rng = np.random.default_rng(20261024)
    for g, s in o.dropna(subset=["grupo"]).groupby("grupo"):
        ninos = s.child_id.unique(); por_nino = {c: s[s.child_id == c] for c in ninos}
        pdn = s.groupby("child_id").agg(r=("y", "sum"), q=("yhat", "sum"))
        bs = [ba(m.y, m.yhat) for m in (pd.concat([por_nino[c] for c in rng.choice(ninos, len(ninos))]) for _ in range(2000))]
        print(f"{nombre} | {g} años | niños {len(ninos)} | % correctas {100 * s.y.mean():.1f} | EB {ba(s.y, s.yhat):.3f} "
              f"(IC {np.percentile(bs, 2.5):.3f} a {np.percentile(bs, 97.5):.3f}) | error PD {(pdn.q - pdn.r).abs().mean():.2f} "
              f"| sesgo {(pdn.q - pdn.r).mean():+.2f}")
