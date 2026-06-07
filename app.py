import streamlit as st
import requests
from datetime import date
import locale

# Configuration de la page Streamlit
st.set_page_config(page_title="Optimiseur de Cartes KSA-TN", layout="wide")
st.title("💳 Outil de Décision Financière : STC Bank vs Al Rajhi")
st.subheader("Analyse ciblée, détails des calculs et calcul des seuils optimaux")

try:
    locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
except Exception:
    try:
        locale.setlocale(locale.LC_TIME, "fr_FR")
    except Exception:
        pass

# 1. Barre latérale : Saisie du montant
st.sidebar.header("💵 Paramètres Financiers")
montant_devise = st.sidebar.number_input("Montant dans la devise de paiement", min_value=1.0, value=1000.0, step=10.0)

@st.cache_data(ttl=3600)
def obtenir_taux_change():
    url = "https://open.er-api.com/v6/latest/SAR"
    try:
        reponse = requests.get(url).json()
        if reponse["result"] == "success":
            return reponse["rates"]
        return None
    except Exception:
        return None

rates = obtenir_taux_change()

if not rates:
    st.error("Impossible de récupérer les taux de change en direct.")
    st.stop()

# 2. Corps principal : Calendrier et choix du pays / opération
st.markdown("### 📅 1. Configuration temporelle de l'opération")
date_operation = st.date_input("Sélectionnez la date de votre transaction :", date.today())

col1, col2 = st.columns(2)

with col1:
    pays = st.radio("📍 2. Choisissez le pays de l'opération :", ["Arabie Saoudite (KSA)", "Tunisie", "France"], horizontal=True)
    
    jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    nom_jour = jours_semaine[date_operation.weekday()]
    date_formatee = f"{nom_jour} {date_operation.strftime('%d/%m/%Y')}"

with col2:
    type_op = st.radio("⚡ 3. Choisissez le type d'opération :", ["Retrait espèce (DAB)", "Paiement en ligne", "Paiement en boutique (TPE)"], horizontal=True)
    
    if "KSA" in pays:
        devise_cible = "SAR"
        st.info("💱 Devise détectée automatiquement : **SAR**")
    elif "Tunisie" in pays:
        devise_cible = "TND"
        st.info("💱 Devise détectée automatiquement : **TND**")
    else:
        devise_cible = st.radio("💱 4. Choisissez la devise de paiement en France :", ["EUR", "USD"], horizontal=True)

# 3. Forcer la période de calcul
st.markdown("### 🗓️ 5. Forcer la période de calcul")
choix_saison = st.tabs(["🍂 Hors période estivale", "☀️ Période estivale (17 mai – 31 août)"])

debut_ete = date(2026, 5, 17)
fin_ete = date(2026, 8, 31)
est_ete_auto = debut_ete <= date_operation <= fin_ete

with choix_saison[0]:
    if not est_ete_auto:
        st.caption("ℹ️ Période sélectionnée par défaut selon votre calendrier.")
with choix_saison[1]:
    if est_ete_auto:
        st.caption("ℹ️ Période sélectionnée par défaut selon votre calendrier.")

est_ete = st.toggle("Activer de force la tarification de la Période Estivale", value=est_ete_auto)
status_saison = "☀️ PÉRIODE ESTIVALE ACTIVE" if est_ete else "❄️ HORS PÉRIODE ESTIVALE"

# 4. Logique de conversion de base
taux_brut = 1.0 if devise_cible == "SAR" else (1 / rates[devise_cible])
valeur_brute_sar = montant_devise * taux_brut

TVA = 0.15
frais_retrait_fixe_stc_int = 23.91 * (1 + TVA)  # 27.50 SAR net

st.write("---")
st.markdown(f"### 📊 Analyse pour : **{type_op}** en **{devise_cible}** ({pays}) | `{status_saison}`")
st.info(f"📈 **Taux du jour ({date_formatee}) :** 1 {devise_cible} = {taux_brut:.4f} SAR | **Valeur brute initiale :** {valeur_brute_sar:.2f} SAR")

# 5. Moteur d'affichage universel
def afficher_details_carte(nom_carte, montant_brut, pct_change, montant_fixe_dab, pct_retrait_int=0.0, is_local_cash_advance=False):
    frais_change_sar = montant_brut * pct_change
    
    frais_dab_sar = 0.0
    texte_detail_retrait = "0.00% + 0.00 SAR"
    
    if is_local_cash_advance:
        frais_dab_sar = (montant_brut * 0.03) * (1 + TVA)
        texte_detail_retrait = f"3.00% local + 15.00% TVA"
    else:
        frais_dab_sar = (montant_brut * pct_retrait_int) + montant_fixe_dab
        if pct_retrait_int > 0 and montant_fixe_dab > 0:
            texte_detail_retrait = f"{pct_retrait_int*100:.2f}% + {montant_fixe_dab:.2f} SAR net"
        elif pct_retrait_int > 0:
            texte_detail_retrait = f"{pct_retrait_int*100:.2f}%"
        elif montant_fixe_dab > 0:
            texte_detail_retrait = f"Fixe : {montant_fixe_dab:.2f} SAR net"
        
    total_debit = montant_brut + frais_change_sar + frais_dab_sar
    
    with st.expander(f"🔍 Détails pour la **{nom_carte}**", expanded=True):
        st.text(f"Base brute convertie : {montant_brut:.2f} SAR")
        st.text(f"Frais de change ({pct_change*100:.2f}%) : {frais_change_sar:.2f} SAR")
        st.text(f"Frais de retrait cumulés ({texte_detail_retrait}) : {frais_dab_sar:.2f} SAR")
        st.markdown(f"**💰 Débit final estimé : {total_debit:.2f} SAR**")
    return total_debit

# 6. Application des grilles tarifaires
fc_stc_sig, ff_stc_sig, local_cash_advance = 0.0, 0.0, False
fc_stc_cla, ff_stc_cla = 0.0, 0.0
fc_rajhi, pct_retrait_rajhi, ff_rajhi, brut_rajhi = 0.0, 0.0, 0.0, valeur_brute_sar

if "KSA" in pays:
    if "Retrait" in type_op:
        local_cash_advance = True  
else:
    if est_ete and ("ligne" not in type_op.lower()):
        fc_stc_sig, ff_stc_sig = 0.0, 0.0
        fc_stc_cla, ff_stc_cla = 0.0, 0.0
    else:
        fc_stc_sig = 0.02
        fc_stc_cla = 0.02
        if "Retrait" in type_op:
            ff_stc_sig = frais_retrait_fixe_stc_int
            ff_stc_cla = frais_retrait_fixe_stc_int

    if devise_cible == "USD":
        brut_rajhi = montant_devise * 3.75
        if "Retrait" in type_op:
            pct_retrait_rajhi = 0.03 
    elif devise_cible == "EUR":
        brut_rajhi = valeur_brute_sar
        if "Retrait" in type_op:
            pct_retrait_rajhi = 0.03
    else:
        fc_rajhi = 0.02
        if "Retrait" in type_op:
            pct_retrait_rajhi = 0.03

# Rendu des colonnes
c1, c2, c3 = st.columns(3)
with c1:
    st.subheader("🥇 STC Visa Signature")
    total_sig = afficher_details_carte("STC Visa Signature", valeur_brute_sar, fc_stc_sig, ff_stc_sig, is_local_cash_advance=local_cash_advance)
with c2:
    st.subheader("🥈 STC Visa Classic")
    total_cla = afficher_details_carte("STC Visa Classic", valeur_brute_sar, fc_stc_cla, ff_stc_cla, is_local_cash_advance=local_cash_advance)
with c3:
    st.subheader("🥉 Al Rajhi Travel Plus")
    total_rajhi = afficher_details_carte("Al Rajhi Travel Plus", brut_rajhi, fc_rajhi, ff_rajhi, pct_retrait_int=pct_retrait_rajhi, is_local_cash_advance=local_cash_advance if "KSA" in pays else False)

# 7. Affichage du Verdict et des Astuces de Seuils
st.write("---")
scores = {"STC Bank Visa Signature": total_sig, "STC Bank Visa Classic": total_cla, "Al Rajhi Travel Plus": total_rajhi}
meilleure_carte = min(scores, key=scores.get)
st.success(f"💡 **Recommandation automatique :** L'option optimale est la **{meilleure_carte}** avec un débit total de **{scores[meilleure_carte]:.2f} SAR**.")

if "Retrait" in type_op and "KSA" not in pays:
    # --- ASTUCE 1 : SEUIL SUR COMPARAISON DES FRAIS UNIQUES DE RETRAIT ---
    seuil_frais_retrait_sar = 27.50 / 0.03
    seuil_frais_retrait_devise = seuil_frais_retrait_sar / taux_brut
    
    st.warning(
        f"🎯 **Astuce 1 : Seuil strict sur Frais de Retrait (Point Mort technique) :** "
        f"Le montant de retrait à partir duquel les 3% d'Al Rajhi dépassent le forfait fixe STC (27,50 SAR) "
        f"est de **{seuil_frais_retrait_devise:.2f} {devise_cible}** ({seuil_frais_retrait_sar:.2f} SAR brut)."
    )
    
    # --- ASTUCE 2 : SEUIL D'ARBITRAGE GLOBAL (SPÉCIFIQUE FRANCE / HORS SÉISON) ---
    if "France" in pays and not est_ete and devise_cible == "EUR":
        seuil_global_sar = 27.50 / 0.01  # Résolution de : 0.03*M = 0.02*M + 27.50
        seuil_global_devise = seuil_global_sar / taux_brut
        
        st.info(
            f"🇪🇺 **Astuce 2 : Seuil d'Arbitrage Global (Zone Euro - Hors Saison) :** "
            f"Grâce aux 2% d'économie sur les frais de change par rapport à STC Bank, vous pouvez retirer avec **Al Rajhi Travel Plus** "
            f"jusqu'à **{seuil_global_devise:.2f} EUR** ({seuil_global_sar:.2f} SAR brut) sans que son coût global ne dépasse vos cartes STC. "
            f"Au-delà de ce montant, l'impact des 3% devient trop lourd et STC Bank reprend l'avantage."
        )
