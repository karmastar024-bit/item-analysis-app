"""Generate the sample datasets in data/ (run once: python -m utils.make_samples).
Deterministic (seeded). Includes deliberately flawed items for teaching."""
import numpy as np, pandas as pd
from pathlib import Path
OUT = Path(__file__).resolve().parent.parent / "data"; OUT.mkdir(exist_ok=True)
rng = np.random.default_rng(2026); N = 40
ability = rng.normal(size=N); ids = [f"S{i:03d}" for i in range(1, N + 1)]

def write(name, key, rows, cols):
    df = pd.DataFrame([["KEY" if name != "written" else "MAX"] + key] + rows,
                      columns=["StudentID"] + cols)
    df.insert(0, "_", None); df = df.drop(columns="_")
    df.to_csv(OUT / f"sample_{name}.csv", index=False)

# ---- MCQ (legacy-style: key + responses in one file for the guide; analyser uses xlsx templates)
cols = [f"Q{i}" for i in range(1, 11)]
key = ["A","B","C","D","A","B","C","D","A","B"]
disc = [1.4,1.2,1.0,0.9,0.8,0.6,0.5,0.3,0.0,-1.0]    # Q10 reversed, Q9 flat
diff = [-0.8,-0.2,0.0,0.3,0.5,0.8,1.2,1.6,0.0,0.0]
rows = []
for s in range(N):
    r = []
    for j, k in enumerate(key):
        pc = 1/(1+np.exp(-(disc[j]*ability[s] - diff[j])))
        if rng.random() < pc: r.append(k)
        else:
            wrong = [o for o in "ABCD" if o != k]
            w = [.7,.3,0.0] if j == 3 else [.5,.3,.2]   # Q4: one dead distractor
            r.append(rng.choice(wrong, p=w))
    rows.append([ids[s]] + r)
write("mcq", key, rows, cols)

# ---- True/False
cols = [f"Q{i}" for i in range(1, 9)]
key = ["True","False","True","True","False","True","False","True"]
disc = [1.3,1.0,0.8,0.6,0.5,0.0,-3.0,1.0]; diff = [0,0.3,-0.3,0.5,0,3.5,0,-4.0]
rows = []
for s in range(N):
    r = []
    for j, k in enumerate(key):
        ok = rng.random() < 1/(1+np.exp(-(disc[j]*ability[s]-diff[j])))
        r.append(k if ok else ("False" if k == "True" else "True"))
    rows.append([ids[s]] + r)
write("true_false", key, rows, cols)

# ---- Fill in the blanks (| separates accepted answers)
cols = [f"Q{i}" for i in range(1, 7)]
key = ["Thimphu","Paro Taktsang|Tiger's Nest|Taktsang","Punakha|Punakha Dzong","Druk","Ngultrum|BTN","Wangchuck"]
wrong = [["Paro","Punakha","Bumthang"],["Thimpu","Paro"],["Wangdue","Trongsa"],["Dragon","Dzong"],["Rupee","Dollar"],["Namgyal","Wangdi"]]
disc = [1.3,1.0,0.8,0.5,0.0,1.5]; diff = [-.5,.2,.6,0,1.5,-.2]
rows = []
for s in range(N):
    r = []
    for j in range(6):
        ok = rng.random() < 1/(1+np.exp(-(disc[j]*ability[s]-diff[j])))
        if ok:
            a = key[j].split("|"); v = str(rng.choice(a))
            v = rng.choice([v, v.upper(), v.lower(), f" {v} "])
            r.append(v)
        else:
            r.append(None if rng.random() < .1 else str(rng.choice(wrong[j])))
    rows.append([ids[s]] + r)
write("fill_blank", key, rows, cols)

# ---- Matching (each prompt = one item, 1 point)
cols = [f"M{i}" for i in range(1, 7)]
key = ["C","A","E","B","D","F"]; opts = list("ABCDEF")
disc = [1.2,1.0,0.8,0.6,0.3,1.4]; diff = [-.4,0,.3,.6,1.0,-1.0]
rows = []
for s in range(N):
    r = []
    for j, k in enumerate(key):
        ok = rng.random() < 1/(1+np.exp(-(disc[j]*ability[s]-diff[j])))
        if ok: r.append(k)
        elif rng.random() < .08: r.append(None)
        else: r.append(str(rng.choice([o for o in opts if o != k])))
    rows.append([ids[s]] + r)
write("matching", key, rows, cols)

# ---- Written (partial credit, different maxima)
cols = ["Q1","Q2","Q3","Q4"]; mx = [5,10,15,20]
rows = []
for s in range(N):
    r = []
    for j, m in enumerate(mx):
        frac = np.clip(0.55 + 0.22*ability[s]*(1.0 if j < 3 else 0.1) + rng.normal(0,.08), 0, 1)
        r.append(round(frac*m*2)/2 if m > 5 else round(frac*m))
    rows.append([ids[s]] + r)
rows[3][2] = None   # one missing score
write("written", mx, rows, cols)
print("written to", OUT)
