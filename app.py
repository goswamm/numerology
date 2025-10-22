import streamlit as st
import pandas as pd
import re
import datetime as dt
from io import BytesIO
from fpdf import FPDF

st.set_page_config(page_title="Numerology Calculator", page_icon="🔢", layout="centered")

PYTHAGOREAN_MAP = {"A":1,"B":2,"C":3,"D":4,"E":5,"F":6,"G":7,"H":8,"I":9,"J":1,"K":2,"L":3,"M":4,"N":5,"O":6,"P":7,"Q":8,"R":9,"S":1,"T":2,"U":3,"V":4,"W":5,"X":6,"Y":7,"Z":8}
CHALDEAN_MAP    = {"A":1,"B":2,"C":3,"D":4,"E":5,"F":8,"G":3,"H":5,"I":1,"J":1,"K":2,"L":3,"M":4,"N":5,"O":7,"P":8,"Q":1,"R":2,"S":3,"T":4,"U":6,"V":6,"W":6,"X":5,"Y":1,"Z":7}
MASTER_NUMBERS = {11,22,33}
VOWELS = set("AEIOU")

def inject_theme(accent_hex="#2E7D32"):
    css = f"""
    <style>
    :root {{ --accent: {accent_hex}; }}
    .stButton>button, .stDownloadButton>button {{
        border-radius: 10px; border: 1px solid var(--accent);
        color: white; background: var(--accent);
    }}
    .stButton>button:hover, .stDownloadButton>button:hover {{ filter: brightness(0.9); }}
    .stTabs [data-baseweb="tab-list"] button[role="tab"][aria-selected="true"] {{ border-bottom: 3px solid var(--accent); }}
    .stMetric {{ border: 1px solid rgba(0,0,0,0.05); border-left: 4px solid var(--accent); padding: 0.25rem 0.5rem; border-radius: 8px; }}
    a {{ color: var(--accent) !important; }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def clean_name(s): return re.sub(r"[^A-Za-z0-9]+", "", s).upper()
def letter_value(c, m, digits): return int(c) if c.isdigit() and digits else m.get(c,0)
def breakdown(name, m, digits): return [(c, letter_value(c,m,digits)) for c in clean_name(name)]
def digital_root(n, keep_master):
    steps=[n]
    while True:
        if keep_master and n in MASTER_NUMBERS: break
        if n<10: break
        n=sum(int(d) for d in str(n)); steps.append(n)
    return n,steps
def alphabet_position(c): 
    return int(c) if c.isdigit() else (ord(c)-64 if "A"<=c<="Z" else 0)

def df_from_breakdown(bd):
    return pd.DataFrame([{"Character":c,"Alphabet #":alphabet_position(c),"Mapped Value":v} for c,v in bd], columns=["Character","Alphabet #","Mapped Value"])

def is_vowel(c, y_as_vowel):
    if c.isdigit(): return False
    if c=="Y": return y_as_vowel
    return c in VOWELS

def split_breakdown(bd, y_as_vowel):
    vowels=[]; consonants=[]
    for c,v in bd:
        if c.isdigit(): continue
        (vowels if is_vowel(c, y_as_vowel) else consonants).append((c,v))
    return vowels, consonants

def reduce_list(values, keep_master):
    total=sum(values); red,steps=digital_root(total, keep_master); return total,red,steps

def compute_numerology(name, system, keep_master, digits):
    m = PYTHAGOREAN_MAP if system=="Pythagorean" else CHALDEAN_MAP
    bd = breakdown(name,m,digits); total=sum(v for _,v in bd); red,steps=digital_root(total, keep_master); return bd,total,red,steps

def _digits_of_int(n): return [int(d) for d in str(n)]
def reduce_number(n, keep_master):
    steps=[n]
    while True:
        if keep_master and n in MASTER_NUMBERS: break
        if n<10: break
        n=sum(_digits_of_int(n)); steps.append(n)
    return n,steps

def compute_life_path(date, keep_master):
    y,y_s=reduce_number(date.year, keep_master); m,m_s=reduce_number(date.month, keep_master); d,d_s=reduce_number(date.day, keep_master)
    total=y+m+d; final,f_s=reduce_number(total, keep_master)
    return {"year":date.year,"month":date.month,"day":date.day,"year_reduced":y,"year_steps":y_s,"month_reduced":m,"month_steps":m_s,"day_reduced":d,"day_steps":d_s,"sum_total":total,"final":final,"final_steps":f_s}

INTERP={1:"Independence, initiative, leadership.",2:"Cooperation, balance, diplomacy.",3:"Creativity, expression, optimism.",4:"Stability, discipline, practicality.",5:"Change, adaptability, curiosity.",6:"Responsibility, care, community.",7:"Analysis, introspection, depth.",8:"Ambition, material drive, management.",9:"Compassion, service, broader vision.",11:"Insight, inspiration, vision (Master 11).",22:"Large-scale building, systems, pragmatism (Master 22).",33:"Service-through-teaching, compassion-in-action (Master 33)."}

st.title("🔢 Numerology Calculator")
inject_theme("#2E7D32")

with st.sidebar:
    st.header("Settings")
    system = st.selectbox("Name Numerology System", ["Pythagorean","Chaldean"], help="Pythagorean: A=1..I=9, J=1..R=9, S=1..Z=8 (cyclical). Chaldean: traditional sound/vibration mapping.")
    keep_master = st.checkbox("Keep master numbers (11, 22, 33)", True)
    digits_as_numbers = st.checkbox("Treat digits in name as numbers", True)
    y_as_vowel = st.checkbox("Treat 'Y' as a vowel for Soul Urge", True)
    show_intermediate = st.checkbox("Show reduction steps", True)
    dob = st.date_input("Birth date (for Life Path)", value=None)

name_input = st.text_input("Enter the full name (person or company)", placeholder="e.g., Ada Lovelace or ACME Innovations Ltd.")
analyze = st.button("Calculate")

if analyze or (name_input and 'autocalc' not in st.session_state) or dob:
    has_name = bool(name_input.strip())
    tabs = st.tabs(["Overview","Breakdown","Vowels & Consonants","Birth Date","Export"])
    df=None
    payload={"input_name":(name_input if has_name else None),"system":system,"keep_master":keep_master,"digits_as_numbers":digits_as_numbers,"y_as_vowel":y_as_vowel,"birth_date":(dob.isoformat() if dob else None),"generated_at":dt.datetime.utcnow().isoformat()+"Z"}

    if has_name:
        bd,total,red,steps = compute_numerology(name_input, system, keep_master, digits_as_numbers)
        payload.update({"cleaned_name":clean_name(name_input),"breakdown":[{"char":c,"value":v} for c,v in bd]})

        with tabs[0]:
            st.subheader("Core Numbers")
            st.metric("Expression / Destiny (Full Name)", red)
            st.caption(f"System: {system} • Master numbers kept: {keep_master} • Digits-as-numbers: {digits_as_numbers}")
            st.write(f"**Interpretation:** {INTERP.get(red,'')}")

        with tabs[1]:
            st.subheader("How this was calculated")
            st.write("**1) Cleaned Name**"); st.code(clean_name(name_input))
            st.write("**2) Character-by-character values**"); df=df_from_breakdown(bd); st.dataframe(df, use_container_width=True)
            st.write("**3) Alphabet → Number representation**")
            st.code("Alphabet positions: " + ' '.join(str(x) for x in df["Alphabet #"]))
            st.code("Mapped values:     " + ' '.join(str(x) for x in df["Mapped Value"]))
            st.write("**4) Total sum (of mapped values)**"); st.code(f"{' + '.join(str(v) for v in df['Mapped Value'])} = {total}")
            st.write("**5) Reduction to final number**"); st.code(' → '.join(str(s) for s in steps) if show_intermediate else str(red))

        with tabs[2]):
            st.subheader("Vowel & Consonant Numbers")
            v_bd,c_bd = split_breakdown(bd,y_as_vowel)
            v_total,v_red,v_steps = reduce_list([v for _,v in v_bd], keep_master)
            c_total,c_red,c_steps = reduce_list([v for _,v in c_bd], keep_master)
            col1,col2 = st.columns(2)
            with col1:
                st.metric("Soul Urge (Vowels)", v_red)
                if show_intermediate and v_steps: st.code(' → '.join(str(s) for s in v_steps))
                st.write(f"**Interpretation:** {INTERP.get(v_red,'')}")
            with col2:
                st.metric("Personality (Consonants)", c_red)
                if show_intermediate and c_steps: st.code(' → '.join(str(s) for s in c_steps))
                st.write(f"**Interpretation:** {INTERP.get(c_red,'')}")
            if v_bd: st.write("**Vowels breakdown**"); st.dataframe(pd.DataFrame(v_bd, columns=["Character","Mapped Value"]), use_container_width=True)
            if c_bd: st.write("**Consonants breakdown**"); st.dataframe(pd.DataFrame(c_bd, columns=["Character","Mapped Value"]), use_container_width=True)
            payload.setdefault("totals",{}).update({"expression_total":total,"expression_reduction_steps":steps,"expression_final":red,"soul_urge_total":v_total,"soul_urge_reduction_steps":v_steps,"soul_urge_final":v_red,"personality_total":c_total,"personality_reduction_steps":c_steps,"personality_final":c_red})

    with tabs[3]:
        st.subheader("Life Path (Birth Date)")
        if dob:
            lp = compute_life_path(dob, keep_master)
            colA,colB,colC = st.columns(3)
            with colA: st.metric("Day reduced", lp["day_reduced"])
            with colB: st.metric("Month reduced", lp["month_reduced"])
            with colC: st.metric("Year reduced", lp["year_reduced"])
            if show_intermediate: st.code(f"{lp['day_reduced']} + {lp['month_reduced']} + {lp['year_reduced']} = {lp['sum_total']} → " + ' → '.join(str(x) for x in lp["final_steps"]))
            st.metric("Life Path Number", lp["final"]); st.write(f"**Interpretation:** {INTERP.get(lp['final'],'')}")
            payload["life_path"]=lp
        else:
            st.info("Select a birth date in the sidebar to compute the Life Path number.")

    with tabs[4]:
        st.subheader("Export")
        if has_name and df is not None:
            csv = df.rename(columns={"Alphabet #":"Alphabet_Number","Mapped Value":"Mapped_Value"}).to_csv(index=False).encode("utf-8")
            st.download_button("Download breakdown CSV", data=csv, file_name="numerology_breakdown.csv", mime="text/csv")
        import json as _json
        st.download_button("Download JSON report", data=_json.dumps(payload, indent=2).encode("utf-8"), file_name="numerology_report.json", mime="application/json")
        def build_pdf(payload:dict)->bytes:
            pdf = FPDF(); pdf.add_page(); pdf.set_auto_page_break(auto=True, margin=15)
            pdf.set_font("Helvetica","B",16); pdf.cell(0,10,"Numerology Report",ln=True,align="C"); pdf.ln(4)
            pdf.set_font("Helvetica","",11)
            if payload.get("input_name"): pdf.multi_cell(0,7,f"Name: {payload['input_name']}")
            pdf.multi_cell(0,7,f"System: {payload['system']}"); pdf.multi_cell(0,7,f"Keep master numbers: {payload['keep_master']}")
            pdf.multi_cell(0,7,f"Digits-as-numbers: {payload['digits_as_numbers']}"); pdf.multi_cell(0,7,f"Y as vowel: {payload['y_as_vowel']}")
            if payload.get("birth_date"): pdf.multi_cell(0,7,f"Birth date: {payload['birth_date']}")
            pdf.multi_cell(0,7,f"Generated at (UTC): {payload['generated_at']}")
            pdf.ln(3); pdf.set_font("Helvetica","B",12); pdf.cell(0,8,"Core Numbers",ln=True)
            pdf.set_font("Helvetica","",11); t=payload.get("totals",{})
            if "expression_final" in t: pdf.multi_cell(0,7,f"Expression/Destiny: {t['expression_final']} — {INTERP.get(t['expression_final'],'')}")
            if "soul_urge_final" in t: pdf.multi_cell(0,7,f"Soul Urge (Vowels): {t['soul_urge_final']} — {INTERP.get(t['soul_urge_final'],'')}")
            if "personality_final" in t: pdf.multi_cell(0,7,f"Personality (Consonants): {t['personality_final']} — {INTERP.get(t['personality_final'],'')}")
            if payload.get("life_path"): pdf.multi_cell(0,7,f"Life Path: {payload['life_path']['final']} — {INTERP.get(payload['life_path']['final'],'')}")
            pdf.ln(3); pdf.set_font("Helvetica","I",10); pdf.multi_cell(0,6,"This report is for educational and entertainment purposes only.")
            out=BytesIO(); pdf.output(out); return out.getvalue()
        if st.button("Generate printable PDF report"):
            try:
                pdf_bytes = build_pdf(payload)
                st.download_button("Download PDF report", data=pdf_bytes, file_name="numerology_report.pdf", mime="application/pdf")
            except Exception as e:
                st.error(f"PDF generation failed: {e}")
else:
    st.info("Enter a name and/or choose a birth date, then click Calculate.")