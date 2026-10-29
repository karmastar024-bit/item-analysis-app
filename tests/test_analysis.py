import numpy as np, pandas as pd, pytest
from scipy import stats
from analysis.decision import decide
from analysis.difficulty import difficulty_binary, difficulty_normalized
from analysis.discrimination import discrimination_ul, group_size, corrected_item_total_r
from analysis.distractor import distractor_efficiency
from analysis.scoring import *
from analysis.binary_analysis import analyze_binary
from analysis.written_analysis import analyze_written
from analysis import statistical_tests as T

# ---------- decision rules ----------
@pytest.mark.parametrize("p,d,de,exp", [
    (.5,.4,None,"RETAIN"), (.87,.4,None,"REVIEW"), (.5,.1,None,"REVIEW"),
    (.14,.1,None,"REVISE"), (.9,.19,None,"REVISE"), (.5,-.01,None,"DISCARD"),
    (1.0,.0,None,"DISCARD"), (0.0,.0,None,"DISCARD"), (.5,.5,0,"DISCARD"),
    (.5,.5,33.33,"RETAIN"), (.2,.2,None,"RETAIN"), (.8,.2,None,"RETAIN")])
def test_decision(p,d,de,exp): assert decide(p,d,de)[0]==exp
def test_decision_reason_text():
    assert decide(.87,.4)[1]=="REVIEW – Difficulty is high (p = 0.87)."
    assert "Difficulty is low (p = 0.14)" in decide(.14,.1)[1]
def test_decision_nan(): assert decide(float("nan"),.3)[0]=="NOT AVAILABLE"

# ---------- difficulty / discrimination ----------
def test_difficulty(): assert difficulty_binary([1,1,0,0])==.5
def test_difficulty_norm(): assert difficulty_normalized([5,10,15],20)==.5
def test_group_size(): assert group_size(100)==27 and group_size(3)==1
def test_discrimination_perfect():
    totals=np.arange(10); item=(totals>=5).astype(int)
    assert discrimination_ul(item,totals)==1.0   # g=2: both upper right, both lower wrong
def test_discrimination_negative():
    totals=np.arange(10); item=(totals<5).astype(int)
    assert discrimination_ul(item,totals)==-1.0
def test_discrimination_zero():
    totals=np.arange(10); item=np.ones(10)
    assert discrimination_ul(item,totals)==0.0
def test_item_total_r_constant_nan():
    assert np.isnan(corrected_item_total_r([1,1,1,1],[3,2,4,1]))

# ---------- distractors ----------
def test_distractor():
    de,det=distractor_efficiency({"A":50,"B":3,"C":40,"D":7},"A",100)
    assert de==pytest.approx(66.67,abs=.01)
    assert [d["functional"] for d in det]==[True,False,True,True]
def test_distractor_matches_legacy():
    from item_analyzer import ItemAnalyzer
    rng=np.random.default_rng(1)
    a=ItemAnalyzer(); a.answer_key={1:"A"}; a.total_questions=1; a.total_students=60
    resp=rng.choice(list("ABCD"),60,p=[.6,.02,.3,.08])
    a.student_data=pd.DataFrame({"responses":[[r] for r in resp]})
    a.calculate_scores()
    it=a.calculate_item_statistics()[0]
    counts={o:int((resp==o).sum()) for o in "ABCD"}
    de,_=distractor_efficiency(counts,"A",60)
    assert de==it.distractor_efficiency
    assert it.difficulty==round(difficulty_binary((resp=="A").astype(int)),2)

# ---------- scoring ----------
def test_tf():
    r=pd.DataFrame({"Q1":["T","true","F",None,"x"]}); s=score_true_false(r,{"Q1":"True"})
    assert s["Q1"].tolist()==[1,1,0,0,0]
def test_fill_multi_case():
    r=pd.DataFrame({"Q1":["Paro","  PARO ","Paro Dzong","Thimphu",None,""]})
    s=score_fill_blank(r,{"Q1":["Paro","paro dzong"]}); assert s["Q1"].tolist()==[1,1,1,0,0,0]
def test_fill_case_sensitive():
    r=pd.DataFrame({"Q1":["Paro","paro"]}); s=score_fill_blank(r,{"Q1":["Paro"]},ignore_case=False)
    assert s["Q1"].tolist()==[1,0]
def test_fill_punct():
    r=pd.DataFrame({"Q1":["H2O.","h2o"]}); s=score_fill_blank(r,{"Q1":["H2O"]},strip_punct=True)
    assert s["Q1"].tolist()==[1,1]
def test_matching_missing():
    r=pd.DataFrame({"M1":["c","C",None,"a"]}); s=score_matching(r,{"M1":"C"})
    assert s["M1"].tolist()==[1,1,0,0]

# ---------- pipelines ----------
def _binary(n=40, seed=0):
    rng=np.random.default_rng(seed); ability=rng.normal(size=n)
    cols={f"G{i}":(ability+rng.normal(0,.6,n)>0).astype(int) for i in range(1,9)}
    cols["Good"]=cols["G1"].copy()
    cols["Easy"]=(rng.random(n)<.97).astype(int); cols["Easy"][0]=0
    cols["AllRight"]=np.ones(n,int); cols["AllWrong"]=np.zeros(n,int)
    cols["Reverse"]=(ability+rng.normal(0,.5,n)<0).astype(int)
    return pd.DataFrame(cols)
def test_binary_pipeline():
    r=analyze_binary(_binary()).set_index("Item")
    assert r.loc["Good","Decision"] in ("RETAIN","REVIEW")
    assert r.loc["AllRight","Decision"]=="DISCARD" and r.loc["AllWrong","Decision"]=="DISCARD"
    assert r.loc["Reverse","Decision"]=="DISCARD"
    assert r.loc["Easy","Decision"] in ("REVIEW","REVISE")
def test_binary_small_sample():
    r=analyze_binary(pd.DataFrame({"Q1":[1,0],"Q2":[1,0]})); assert len(r)==2
def test_written_max_scores_and_missing():
    rng=np.random.default_rng(3); n=30; ab=rng.normal(size=n)
    df=pd.DataFrame({"Q1":np.clip(np.round(5*(ab+2)/4),0,5),"Q2":np.clip(np.round(10*(ab+2)/4),0,10),
                     "Q3":np.clip(np.round(15*(ab+2)/4),0,15)})
    df.loc[0,"Q2"]=np.nan
    r=analyze_written(df,{"Q1":5,"Q2":10,"Q3":15}).set_index("Item")
    assert r.loc["Q2","Missing Scores"]==1
    assert all(r["Discrimination (D)"]>0.3)
    assert r.loc["Q3","Difficulty (p = mean/max)"]==pytest.approx(df["Q3"].mean()/15,abs=.01)

# ---------- statistical tests vs scipy ----------
A=[10,12,14,15,18,20,22,19,17]; B=[8,9,12,13,14,15,16,11,10]
def test_t1():
    r=T.one_sample_t(A,12); ref=stats.ttest_1samp(A,12)
    assert r["statistic"]==pytest.approx(ref.statistic) and r["p_value"]==pytest.approx(ref.pvalue)
    assert r["df"]==len(A)-1
def test_t1_one_sided():
    r=T.one_sample_t(A,12,alt="greater"); ref=stats.ttest_1samp(A,12,alternative="greater")
    assert r["p_value"]==pytest.approx(ref.pvalue)
def test_welch():
    r=T.independent_t(A,B); ref=stats.ttest_ind(A,B,equal_var=False)
    assert r["statistic"]==pytest.approx(ref.statistic) and r["p_value"]==pytest.approx(ref.pvalue)
def test_pooled():
    r=T.independent_t(A,B,equal_var=True); ref=stats.ttest_ind(A,B)
    assert r["p_value"]==pytest.approx(ref.pvalue) and r["df"]==len(A)+len(B)-2
def test_paired():
    r=T.paired_t(B,A); ref=stats.ttest_rel(A,B)
    assert r["statistic"]==pytest.approx(ref.statistic) and r["p_value"]==pytest.approx(ref.pvalue)
def test_ci_contains_estimate():
    r=T.one_sample_t(A,12); assert r["ci"][0]<np.mean(A)<r["ci"][1]
def test_z1():
    r=T.one_sample_z(A,12,4); z=(np.mean(A)-12)/(4/3)
    assert r["statistic"]==pytest.approx(z) and r["p_value"]==pytest.approx(2*stats.norm.sf(abs(z)))
    assert r["warnings"]
def test_z2():
    r=T.two_sample_z(A,B,4,5); z=(np.mean(A)-np.mean(B))/np.sqrt(16/9+25/9)
    assert r["statistic"]==pytest.approx(z)
def test_alpha_changes_decision():
    r1=T.one_sample_t(A,13.5,alpha=.05); r2=T.one_sample_t(A,13.5,alpha=.5)
    assert r2["decision"]=="Reject H0"
@pytest.mark.parametrize("fn,args",[
    (T.one_sample_t,([5],1)), (T.one_sample_t,([5,5,5],1)), (T.independent_t,([1],[2,3])),
    (T.paired_t,([1,2],[1,2,3])), (T.paired_t,([1,2,3],[2,3,4])),
    (T.one_sample_z,([1,2],1,0)), (T.two_sample_z,([1],[2],1,-1))])
def test_bad_inputs_raise_valueerror(fn,args):
    with pytest.raises(ValueError): fn(*args)
def test_descriptive():
    d=T.descriptive([1,2,2,3,3,4]); assert d["Mode"]=="2, 3" and d["Range"]==3
    assert d["Variance (sample)"]==pytest.approx(1.1)
