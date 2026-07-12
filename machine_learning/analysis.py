"""
analysis.py - Descriptive, Diagnostic, Predictive & Prescriptive Analysis
TikTok-only. 5,331 rows, 13 businesses, Jan 2024 to Jul 2026.
Run from machine_learning/ folder.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import os, json, warnings
warnings.filterwarnings("ignore")

# Soft rose editorial theme (frontend/src/theme.js)
BG="#FFF9F6"; INK="#45372E"; TEXT="#5C4B43"; MUTED="#A18E84"; GRID="#5C4B4314"; BORDER="#EBE0DA"
plt.rcParams.update({
    "font.family":"sans-serif",
    "figure.facecolor":BG,"savefig.facecolor":BG,"axes.facecolor":BG,
    "axes.edgecolor":BORDER,"axes.labelcolor":TEXT,"text.color":INK,
    "xtick.color":MUTED,"ytick.color":MUTED,
    "axes.spines.top":False,"axes.spines.right":False,
    "axes.grid":True,"grid.color":GRID,"grid.linewidth":0.8,"grid.linestyle":"--",
    "figure.dpi":130,"savefig.dpi":300,
})
TT="#FF7EA5"; GOOD="#3AA876"; WARN="#D98A2B"; BAD="#E5484D"; PURP="#B33E5D"  # rose theme
DAY_NAMES=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

# ── Load ──────────────────────────────────────────────────────────────────────
def load_data():
    for fname in ["merged_features.csv","merged_augmented.csv","merged_cleaned.csv"]:
        if os.path.exists(fname):
            print(f"   Loading from {fname}")
            df = pd.read_csv(fname)
            df["post_date"] = pd.to_datetime(df["post_date"])
            return df[df["post_date"] >= "2024-01-01"].copy()
    print("   Loading from finaltiktokdata.csv")
    df = pd.read_csv("finaltiktokdata.csv")
    df.columns = df.columns.str.strip().str.lower()
    df["post_date"] = pd.to_datetime(df["post_date"])
    df = df[df["post_date"] >= "2024-01-01"].copy()
    unique_biz = sorted(df["business"].dropna().unique())
    biz_map = {n: f"Business{i+1}" for i,n in enumerate(unique_biz)}
    df["business"] = df["business"].map(biz_map)
    return df

df = load_data()
if "eng_score" not in df.columns and "engagement_score" in df.columns:
    df["eng_score"] = df["engagement_score"]
elif "eng_score" not in df.columns:
    df["eng_score"] = (df["likes"]+3*df["comments"]+2*df["shares"]+df["saves"].fillna(0))/df["views"].replace(0,np.nan)

df["month_num"]  = pd.to_datetime(df["post_date"]).dt.month
df["day_num"]    = pd.to_datetime(df["post_date"]).dt.dayofweek
df["is_weekend"] = df["day_num"].isin([5,6])
df["is_festival"]= df["month_num"].isin([3,10,11])
print(f"Loaded {len(df)} rows - {df['business'].nunique()} businesses\n")

# ── Precompute buckets ────────────────────────────────────────────────────────
df["cap_bucket"] = pd.cut(df["caption_length"],bins=[0,50,150,300,10000],labels=["Short\n<50","Medium\n50-150","Long\n150-300","V.Long\n>300"])
df["ht_bucket"]  = pd.cut(df["hashtag_count"],bins=[-1,3,7,12,20,100],labels=["1-3","4-7","8-12","13-20","20+"])
df["dur_bucket"] = pd.cut(df["video_duration_sec"],bins=[0,15,30,60,300],labels=["<15s","15-30s","30-60s",">60s"])

ht_stats  = df.groupby("ht_bucket")["eng_score"].mean()
cap_stats = df.groupby("cap_bucket").agg(avg_ht=("hashtag_count","mean"),avg_eng=("eng_score","mean"))
dur_stats = df.groupby("dur_bucket")["eng_score"].mean()
wd_eng    = df.groupby("is_weekend")["eng_score"].mean()
fest_eng  = df.groupby("is_festival")["eng_score"].mean()
biz_stats = df.groupby("business")["eng_score"].agg(["mean","count"]).rename(columns={"mean":"avg","count":"posts"}).sort_values("avg",ascending=True)
hourly    = df.groupby("hour")["likes"].mean().reindex(range(24),fill_value=0)
top3h     = hourly.nlargest(3).index

print("Building DESCRIPTIVE charts...")
# DESC 1 monthly
monthly = df.groupby(df["post_date"].dt.to_period("M")).size()
monthly.index = monthly.index.astype(str)
fig,ax = plt.subplots(figsize=(14,4))
bars = ax.bar(monthly.index,monthly.values,color=TT,alpha=0.85,width=0.7)
peak_idx = monthly.values.argmax()
bars[peak_idx].set_color(GOOD)
ax.text(peak_idx,monthly.values[peak_idx]+5,f"Peak\n{monthly.values[peak_idx]}",ha="center",fontsize=8,color=GOOD)
ax.set_xticks(range(0,len(monthly),2))
ax.set_xticklabels(list(monthly.index)[::2],rotation=30,ha="right",fontsize=9)
ax.set_ylabel("Posts"); ax.set_title("Monthly TikTok Posting Volume - Jan 2024 to Jul 2026",fontsize=13,pad=10)
plt.tight_layout(); plt.savefig("desc_1_monthly_trend.png",bbox_inches="tight"); plt.close()
print("  desc_1_monthly_trend.png")

# DESC 2 hourly likes
fig,ax = plt.subplots(figsize=(12,4))
colors_h=[GOOD if h in top3h else TT+"99" for h in range(24)]
ax.bar(hourly.index,hourly.values,color=colors_h,width=0.8)
for h in top3h: ax.text(h,hourly[h]+50,f"{h:02d}h",ha="center",fontsize=8,color=GOOD,fontweight="bold")
ax.set_xlabel("Hour (NPT)"); ax.set_ylabel("Avg likes")
ax.set_title("TikTok - Average Likes by Hour (NPT)\nPeak: midnight–3am",fontsize=12,pad=10)
ax.set_xticks(range(0,24,2))
plt.tight_layout(); plt.savefig("desc_2_hourly_engagement.png",bbox_inches="tight"); plt.close()
print("  desc_2_hourly_engagement.png")

# DESC 3 business comparison
fig,ax = plt.subplots(figsize=(10,6))
colors_b=[GOOD if i==len(biz_stats)-1 else TT for i in range(len(biz_stats))]
ax.barh(biz_stats.index,biz_stats["avg"],color=colors_b,alpha=0.85)
for i,(idx,row) in enumerate(biz_stats.iterrows()):
    ax.text(row["avg"]*1.01,i,f"n={int(row['posts'])}",va="center",fontsize=8,color="gray")
ax.set_xlabel("Avg engagement score")
ax.set_title("TikTok - Business Engagement Score Comparison",fontsize=12,pad=10)
plt.tight_layout(); plt.savefig("desc_3_business_comparison.png",bbox_inches="tight"); plt.close()
print("  desc_3_business_comparison.png")

# DESC 4 weekday/festival
diff_wd = (wd_eng[True]-wd_eng[False])/wd_eng[False]*100
diff_f  = (fest_eng[True]-fest_eng[False])/fest_eng[False]*100
fig,axes = plt.subplots(1,2,figsize=(12,4))
axes[0].bar(["Weekday","Weekend"],[wd_eng[False],wd_eng[True]],color=[TT,GOOD if wd_eng[True]>wd_eng[False] else BAD],alpha=0.85)
axes[0].set_title("Weekday vs Weekend",fontsize=11); axes[0].set_ylabel("Avg engagement score")
axes[0].text(1,wd_eng[True]*1.01,f"{diff_wd:+.1f}%",ha="center",fontsize=10,color=GOOD if diff_wd>0 else BAD)
axes[1].bar(["Regular","Festival\nMar/Oct/Nov"],[fest_eng[False],fest_eng[True]],color=[TT,GOOD if fest_eng[True]>fest_eng[False] else BAD],alpha=0.85)
axes[1].set_title("Festival vs Regular Month",fontsize=11); axes[1].set_ylabel("Avg engagement score")
axes[1].text(1,fest_eng[True]*1.01,f"{diff_f:+.1f}%",ha="center",fontsize=10,color=GOOD if diff_f>0 else BAD)
plt.tight_layout(); plt.savefig("desc_4_weekday_festival.png",bbox_inches="tight"); plt.close()
print("  desc_4_weekday_festival.png")

print("\nBuilding DIAGNOSTIC charts...")
# DIAG 1 volume vs quality
corr = biz_stats["posts"].corr(biz_stats["avg"])
fig,ax = plt.subplots(figsize=(8,5))
sizes=(biz_stats["posts"]/biz_stats["posts"].max())*600+80
ax.scatter(biz_stats["posts"],biz_stats["avg"],s=sizes,color=TT,alpha=0.75,edgecolors="black",linewidth=0.5)
z=np.polyfit(biz_stats["posts"],biz_stats["avg"],1)
xl=np.linspace(biz_stats["posts"].min(),biz_stats["posts"].max(),50)
ax.plot(xl,np.poly1d(z)(xl),"k--",linewidth=1.2,alpha=0.7)
for _,row in biz_stats.iterrows(): ax.annotate(row.name,(row["posts"],row["avg"]),xytext=(5,3),textcoords="offset points",fontsize=8,alpha=0.8)
ax.set_xlabel("Posts (volume)"); ax.set_ylabel("Avg engagement (quality)")
ax.set_title(f"WHY: Volume vs Quality - correlation={corr:.3f}\n(weak negative: posting more does not build engagement)",fontsize=11,pad=10)
plt.tight_layout(); plt.savefig("diag_1_volume_vs_quality.png",bbox_inches="tight"); plt.close()
print("  diag_1_volume_vs_quality.png")

# DIAG 2 caption vs hashtag
fig,axes = plt.subplots(1,2,figsize=(12,4.5))
colors_c=[GOOD if v==cap_stats["avg_eng"].max() else TT for v in cap_stats["avg_eng"]]
axes[0].bar(cap_stats.index,cap_stats["avg_eng"],color=colors_c,alpha=0.85)
ax2=axes[0].twinx(); ax2.plot(cap_stats.index,cap_stats["avg_ht"],color=BAD,marker="o",linewidth=2)
ax2.set_ylabel("Avg hashtag count",color=BAD); ax2.tick_params(axis="y",colors=BAD)
axes[0].set_title("Caption length effect\n(medium captions also use more hashtags)",fontsize=11)
axes[0].set_ylabel("Avg engagement score")
colors_h2=[GOOD if v==ht_stats.max() else TT for v in ht_stats]
axes[1].bar(ht_stats.index,ht_stats.values,color=colors_h2,alpha=0.85)
axes[1].text(list(ht_stats.index).index(ht_stats.idxmax()),ht_stats.max()*1.01,"optimal ✓",ha="center",fontsize=9,color=GOOD)
axes[1].set_title("WHY: 4-7 hashtags directly drives most engagement",fontsize=11)
axes[1].set_ylabel("Avg engagement score")
plt.tight_layout(); plt.savefig("diag_2_caption_hashtag.png",bbox_inches="tight"); plt.close()
print("  diag_2_caption_hashtag.png")

# DIAG 3 duration
fig,ax = plt.subplots(figsize=(7,4))
colors_d=[GOOD if v==dur_stats.max() else TT for v in dur_stats]
ax.bar(dur_stats.index,dur_stats.values,color=colors_d,alpha=0.85)
ax.text(list(dur_stats.index).index(dur_stats.idxmax()),dur_stats.max()*1.01,"best ✓",ha="center",fontsize=9,color=GOOD)
ax.set_xlabel("Video duration"); ax.set_ylabel("Avg engagement score")
ax.set_title("WHY: 15-30s videos outperform\nMatches TikTok short-form preference",fontsize=11,pad=10)
plt.tight_layout(); plt.savefig("diag_3_duration_effect.png",bbox_inches="tight"); plt.close()
print("  diag_3_duration_effect.png")

# DIAG 4 festival reality
fig,ax = plt.subplots(figsize=(6,4))
ax.bar(["Regular","Festival\nMar/Oct/Nov"],[fest_eng[False],fest_eng[True]],
       color=[TT,GOOD if fest_eng[True]>fest_eng[False] else BAD],alpha=0.85)
ax.set_ylabel("Avg engagement score")
ax.set_title(f"WHY: Festival engagement is {diff_f:+.1f}%\nBusinesses post MORE but quality stays flat",fontsize=11,pad=10)
plt.tight_layout(); plt.savefig("diag_4_festival_reality.png",bbox_inches="tight"); plt.close()
print("  diag_4_festival_reality.png")

print("\nBuilding PREDICTIVE charts...")
model_path=os.path.join("model_package","model_best.joblib")
if not os.path.exists(model_path):
    print("  model_best.joblib not found - run steps 7.1-7.4 first")
else:
    import joblib
    model=joblib.load(model_path); scaler=joblib.load(os.path.join("model_package","scaler.joblib"))
    with open(os.path.join("model_package","feature_cols.json")) as f: FEATURE_COLS=json.load(f)
    with open(os.path.join("model_package","best_model_name.txt")) as f: MODEL_NAME=f.read().strip()
    train_df=pd.read_csv("train_set.csv"); test_df=pd.read_csv("test_set.csv")
    eng_col="engagement_score" if "engagement_score" in test_df.columns else "eng_score"
    X_test=scaler.transform(test_df[FEATURE_COLS].fillna(0)); y_test=test_df[eng_col].values; y_pred=model.predict(X_test)
    from sklearn.metrics import mean_squared_error,mean_absolute_error,r2_score
    rmse=np.sqrt(mean_squared_error(y_test,y_pred)); mae=mean_absolute_error(y_test,y_pred); r2=r2_score(y_test,y_pred)
    print(f"  {MODEL_NAME}: R²={r2:.4f} ({r2*100:.1f}%), RMSE={rmse:.5f}, MAE={mae:.5f}")
    fig,axes=plt.subplots(1,2,figsize=(13,5))
    axes[0].scatter(y_test,y_pred,alpha=0.3,s=12,color=TT)
    lim=max(y_test.max(),y_pred.max())*1.05
    axes[0].plot([0,lim],[0,lim],"k--",linewidth=1,label="Perfect prediction")
    axes[0].set_xlabel("Actual"); axes[0].set_ylabel("Predicted")
    axes[0].set_title(f"{MODEL_NAME} - Actual vs Predicted",fontsize=11); axes[0].legend(fontsize=9)
    axes[0].text(0.05,0.92,f"R² = {r2*100:.1f}%\nRMSE = {rmse:.5f}\nMAE = {mae:.5f}",transform=axes[0].transAxes,fontsize=9,bbox=dict(boxstyle="round,pad=0.4",facecolor="white",alpha=0.8))
    residuals=y_test-y_pred
    axes[1].hist(residuals,bins=50,color=PURP,alpha=0.8,edgecolor="white")
    axes[1].axvline(0,color="black",linestyle="--",linewidth=1.2)
    axes[1].set_xlabel("Residual"); axes[1].set_ylabel("Count"); axes[1].set_title("Residual Distribution",fontsize=11)
    plt.suptitle("Predictive Model Performance",fontsize=13,y=1.02)
    plt.tight_layout(); plt.savefig("pred_1_model_performance.png",bbox_inches="tight"); plt.close()
    print("  pred_1_model_performance.png")
    feat_df=pd.DataFrame({"feature":FEATURE_COLS,"importance":model.feature_importances_}).sort_values("importance",ascending=True).tail(15)
    def fc(f):
        if f in ["hour_sin","hour_cos","dow_sin","dow_cos"]: return "#B33E5D"  # cyclical time - deep rose
        if f in ["is_weekend","is_festival","is_lunch_hour","is_evening"]: return GOOD
        if "rate" in f: return TT
        if f=="followers_log": return "#FF7EA5"  # account size - primary rose
        return "#B79F97"  # content - warm mauve
    fig,ax=plt.subplots(figsize=(9,6))
    ax.barh(feat_df["feature"],feat_df["importance"],color=[fc(f) for f in feat_df["feature"]],edgecolor="white")
    ax.set_xlabel("Feature importance"); ax.set_title(f"Top Features - {MODEL_NAME}",fontsize=12,pad=10)
    legend=[mpatches.Patch(color="#B33E5D",label="Cyclical time"),mpatches.Patch(color=GOOD,label="Nepal calendar"),mpatches.Patch(color=TT,label="Engagement rates"),mpatches.Patch(color="#FF7EA5",label="Account size")]
    ax.legend(handles=legend,fontsize=8,loc="lower right")
    plt.tight_layout(); plt.savefig("pred_2_feature_importance.png",bbox_inches="tight"); plt.close()
    print("  pred_2_feature_importance.png")

print("\nBuilding PRESCRIPTIVE charts...")
# PRESC 1 hour x day heatmap
day_hour=df.groupby(["day_num","hour"])["eng_score"].mean().unstack(fill_value=0)
day_hour.index=[DAY_NAMES[i] for i in day_hour.index]
fig,ax=plt.subplots(figsize=(14,4))
sns.heatmap(day_hour,ax=ax,cmap="YlOrRd",linewidths=0.3,cbar_kws={"label":"Avg engagement score"},
            xticklabels=[f"{h:02d}h" if h%2==0 else "" for h in range(24)])
ax.set_title("WHAT TO DO: Best Day × Hour to Post on TikTok (NPT)",fontsize=12,pad=10)
ax.set_xlabel("Hour (NPT)"); ax.set_ylabel("Day")
plt.tight_layout(); plt.savefig("presc_1_hour_day_heatmap.png",bbox_inches="tight"); plt.close()
print("  presc_1_hour_day_heatmap.png")

# PRESC 2 content advice
fig,axes=plt.subplots(1,3,figsize=(14,4))
colors_ht2=[GOOD if v==ht_stats.max() else TT+"99" for v in ht_stats]
axes[0].bar(ht_stats.index,ht_stats.values,color=colors_ht2,alpha=0.9)
axes[0].set_title("Hashtags: use 4-7",fontsize=10); axes[0].set_ylabel("Avg engagement score")
cap_eng=df.groupby("cap_bucket")["eng_score"].mean()
colors_cap2=[GOOD if v==cap_eng.max() else TT+"99" for v in cap_eng]
axes[1].bar(cap_eng.index,cap_eng.values,color=colors_cap2,alpha=0.9)
axes[1].set_title("Caption: 50-150 chars",fontsize=10); axes[1].set_ylabel("Avg engagement score")
colors_dur2=[GOOD if v==dur_stats.max() else TT+"99" for v in dur_stats]
axes[2].bar(dur_stats.index,dur_stats.values,color=colors_dur2,alpha=0.9)
axes[2].set_title("Duration: 15-30 seconds",fontsize=10); axes[2].set_ylabel("Avg engagement score")
plt.suptitle("TikTok Content Prescription - What to post for maximum engagement",fontsize=12,y=1.02)
plt.tight_layout(); plt.savefig("presc_2_content_advice.png",bbox_inches="tight"); plt.close()
print("  presc_2_content_advice.png")

# PRESC 3 action plan
best_hour=int(df.groupby("hour")["eng_score"].mean().idxmax())
best_day=int(df.groupby("day_num")["eng_score"].mean().idxmax())
action=pd.DataFrame([{
    "Platform":"TikTok","Best hour (NPT)":f"{best_hour:02d}:00","Best day":DAY_NAMES[best_day],
    "Hashtags":str(ht_stats.idxmax()),"Caption length":str(cap_eng.idxmax()),
    "Video duration":str(dur_stats.idxmax()),
    "Weekend effect":f"{diff_wd:+.1f}% vs weekday","Festival effect":f"{diff_f:+.1f}% vs regular",
    "Key insight 1":f"Post at {best_hour:02d}:00 on {DAY_NAMES[best_day]} NPT",
    "Key insight 2":"Midnight-3am gets highest likes (Nepal midnight scroll culture)",
    "Key insight 3":f"Use {ht_stats.idxmax()} hashtags and {cap_eng.idxmax()} captions",
    "Key insight 4":f"Keep videos {dur_stats.idxmax()} - short-form outperforms",
}])
action.to_csv("presc_3_action_plan.csv",index=False)
print("  presc_3_action_plan.csv")
print("\n✅ ALL 4 ANALYSES COMPLETE")