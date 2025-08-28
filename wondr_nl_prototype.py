
import pandas as pd
import numpy as np
import re
from datetime import datetime
import argparse
from pathlib import Path

def read_csv_flexible(path):
    return pd.read_csv(path, engine="python", sep=None)

def preprocess(tx: pd.DataFrame, profiles: pd.DataFrame):
    df = tx.copy()
    df["trx_dt"] = pd.to_datetime(df["trx_date"], errors="coerce")
    df["amount_num"] = pd.to_numeric(df["amount"], errors="coerce")
    dc = df["debit_credit"].astype(str).str.upper().str.strip()
    df["is_debit"] = dc.eq("DEBIT")
    df["is_credit"] = dc.eq("CREDIT")
    df["signed_amount"] = np.where(df["is_debit"], -df["amount_num"], df["amount_num"])
    def infer_category(row):
        texts = " ".join([
            str(row.get("detail_information", "")),
            str(row.get("subheader", "")),
            str(row.get("notes", "")),
            str(row.get("tags", "")),
        ]).lower()
        CAT_MAP = {
            "coffee": ["coffee", "kopi", "starbucks", "kopitiam"],
            "groceries": ["grocery", "groceries", "supermarket", "hypermart", "carrefour", "giant", "alfamart", "indomaret"],
            "restaurants": ["restaurant", "restaurants", "diner", "cafe", "warung", "mcd", "kfc", "bk", "pizza", "sushi", "bakso", "mie"],
            "shopping": ["shopping", "fashion", "clothes", "apparel", "mall", "tokopedia", "shopee", "lazada", "zalora", "uniqlo"],
            "gas": ["gas", "fuel", "pertamina", "spbu", "shell", "bp"],
            "transportation": ["transport", "gojek", "grab", "transjakarta", "mrt", "lrt", "uber", "bluebird", "train"],
            "utilities": ["utility", "utilities", "pln", "electric", "electricity", "pdam", "water", "internet", "wifi", "telkom", "indihome", "telco"],
            "healthcare": ["hospital", "clinic", "doctor", "pharmacy", "apotek", "bpjs"],
            "education": ["school", "tuition", "education", "course", "kuliah", "bimbel", "udemy", "coursera"],
            "entertainment": ["entertainment", "netflix", "spotify", "disney", "cinema", "bioskop", "game", "steam"],
            "rent": ["rent", "sewa", "kost", "kos", "apartment", "apartemen", "boarding"],
            "insurance": ["insurance", "asuransi", "premium"],
            "fees": ["fee", "fees", "admin", "charge", "interest"],
            "salary": ["salary", "gaji", "payroll"],
            "transfer": ["transfer", "topup", "top up", "withdraw", "cash out", "cashout", "cash in"],
            "refund": ["refund", "reversal"],
            "travel": ["hotel", "airasia", "garuda", "citilink", "traveloka", "booking", "agoda", "expedia", "pesawat", "flight", "airport"],
        }
        for cat, kws in CAT_MAP.items():
            if any(kw in texts for kw in kws):
                return cat
        code = str(row.get("category_by_system", "")).strip()
        CODE_MAP = {"1":"groceries","2":"restaurants","3":"shopping","4":"gas","5":"utilities","6":"transportation","7":"healthcare","8":"education","9":"entertainment","10":"fees"}
        if code in CODE_MAP:
            return CODE_MAP[code]
        return "other"
    df["category_inferred"] = df.apply(infer_category, axis=1)
    prof = profiles.copy()
    prof["cif"] = prof["cif"].astype(str)
    df["cif"] = df["cif"].astype(str)
    df = df.merge(prof[["cif","customer_name","age_group","income_bracket","region","account_type","risk_profile"]], on="cif", how="left")
    return df

MONTHS = {m.lower(): i for i, m in enumerate(["January","February","March","April","May","June","July","August","September","October","November","December"], start=1)}
MONTHS.update({m[:3].lower(): i for m,i in MONTHS.items()})

def parse_daterange(text, today=None):
    import pandas as pd
    if today is None:
        today = pd.Timestamp.today().normalize()
    text = text.lower()
    m = re.search(r"last\s+(\d+)\s+months?", text)
    if m:
        n = int(m.group(1))
        end = (today + pd.offsets.MonthEnd(0))
        start = (end - pd.DateOffset(months=n-1)).replace(day=1)
        return pd.Timestamp(start), pd.Timestamp(end)
    if "last month" in text:
        first_of_this_month = today.replace(day=1)
        last_month_end = first_of_this_month - pd.Timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        return pd.Timestamp(last_month_start), pd.Timestamp(last_month_end)
    if "this year" in text or "year to date" in text or "ytd" in text:
        start = pd.Timestamp(year=today.year, month=1, day=1)
        return start, today
    m = re.search(r"(in\s+)?([a-zA-Z]{3,9})\s+(\d{4})", text)
    if m:
        mon_name = m.group(2)[:3].lower()
        year = int(m.group(3))
        month = MONTHS.get(mon_name, None)
        if month:
            start = pd.Timestamp(year=year, month=month, day=1)
            end = (start + pd.offsets.MonthEnd(0))
            return start, end
    if "last week" in text:
        weekday = today.weekday()
        last_sunday = today - pd.Timedelta(days=weekday+1)
        last_monday = last_sunday - pd.Timedelta(days=6)
        return last_monday, last_sunday
    return today - pd.Timedelta(days=30), today

def clean_category_keyword(raw: str) -> str:
    s = raw.strip()
    s = re.sub(r"\b(last|this)\s+(month|week|year)\b", "", s)
    s = re.sub(r"\blast\s+\d+\s+months?\b", "", s)
    s = re.sub(r"\bin\s+[a-zA-Z]{3,9}\s+\d{4}\b", "", s)
    return re.sub(r"\s{2,}", " ", s).strip()

def resolve_customer_id(df, query_text=None):
    if not query_text:
        return df["cif"].iloc[0]
    q = str(query_text).lower()
    for c in df["cif"].astype(str).unique().tolist():
        if c in q:
            return str(c)
    names = df[["cif","customer_name"]].dropna().drop_duplicates()
    for _, row in names.iterrows():
        if str(row["customer_name"]).lower() in q:
            return str(row["cif"])
    last_by_cif = df.groupby("cif")["trx_dt"].max().sort_values(ascending=False)
    return str(last_by_cif.index[0])

def aggregate(df, cif, start, end):
    d = df[(df["cif"]==str(cif)) & (df["trx_dt"]>=pd.Timestamp(start)) & (df["trx_dt"]<=pd.Timestamp(end))].copy()
    spent = d.loc[d["is_debit"], "amount_num"].sum()
    income = d.loc[d["is_credit"], "amount_num"].sum()
    net = income - spent
    by_cat = d.loc[d["is_debit"]].groupby("category_inferred")["amount_num"].sum().sort_values(ascending=False)
    return d, float(spent), float(income), float(net), by_cat

def answer_query(df, text, customer_hint=None, today=None):
    if today is None:
        today = df["trx_dt"].max()
    start, end = parse_daterange(text, today=today)
    data_end = df["trx_dt"].max().normalize()
    if end > data_end:
        end = data_end
    cif = resolve_customer_id(df, customer_hint or text)
    d, spent, income, net, by_cat = aggregate(df, cif, start, end)
    tl = text.lower()
    if ("biggest" in tl or "top" in tl or "largest" in tl) and "category" in tl and ("spend" in tl or "spending" in tl):
        cat = None if by_cat.empty else by_cat.index[0]
        amt = 0.0 if by_cat.empty else float(by_cat.iloc[0])
        return f"[{cif}] Biggest spending category from {start.date()} to {end.date()}: {cat} ({amt:,.0f})."
    m = re.search(r"spen[dt]\s+on\s+([a-zA-Z ]+)", tl)
    cat_kw = None
    if m:
        cat_kw = clean_category_keyword(m.group(1))
    else:
        m2 = re.search(r"how much .* (?:on )?([a-zA-Z ]+)", tl)
        if m2 and ("spend" in tl or "spent" in tl):
            cat_kw = clean_category_keyword(m2.group(1))
    if cat_kw:
        mask_cat = (
            d["category_inferred"].str.contains(cat_kw.split()[0], na=False) |
            d[["detail_information","subheader","notes","tags"]].astype(str).apply(lambda col: col.str.lower().str.contains(cat_kw), axis=0).any(axis=1)
        ) & d["is_debit"]
        total = d.loc[mask_cat, "amount_num"].sum()
        return f"[{cif}] Spend on {cat_kw} from {start.date()} to {end.date()}: {total:,.0f}."
    if "save" in tl or "saving" in tl:
        return f"[{cif}] Estimated savings {start.date()} to {end.date()}: {net:,.0f} (income {income:,.0f} - spend {spent:,.0f})."
    return f"[{cif}] Summary {start.date()} to {end.date()}: spent {spent:,.0f}, income {income:,.0f}, net {net:,.0f}."

def main():
    p = argparse.ArgumentParser(description="Wondr mini NL prototype")
    p.add_argument("--transactions", default="transactions.csv")
    p.add_argument("--profiles", default="customer_profiles.csv")
    p.add_argument("--query", required=True, help="Natural language question")
    p.add_argument("--customer", default=None, help="Customer name or CIF in the query context")
    args = p.parse_args()
    tx = read_csv_flexible(args.transactions)
    profiles = read_csv_flexible(args.profiles)
    df = preprocess(tx, profiles)
    print(answer_query(df, args.query, customer_hint=args.customer))

if __name__ == "__main__":
    main()
