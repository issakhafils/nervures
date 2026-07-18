import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon, FancyBboxPatch, Arrow
from matplotlib.lines import Line2D
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
import io
import tempfile
import os
from math import ceil
from datetime import datetime

st.set_page_config(
    page_title="Calcul Dalle Nervurée EC2",
    page_icon="🏗️",
    layout="wide"
)

# ============================================
# TITRE PRINCIPAL
# ============================================
st.title("🏗️ Calcul de Dalle Nervurée - EC2 Simplifié")
st.markdown("*Outil de dimensionnement simplifié pour dalle nervurée*")

# ============================================
# SIDEBAR - PARAMÈTRES D'ENTRÉE
# ============================================
st.sidebar.header("📋 Paramètres d'entrée")

# Dimensions du panneau
st.sidebar.subheader("Dimensions du panneau")
Bp = st.sidebar.number_input("Largeur panneau Bp (m)", min_value=2.0, max_value=20.0, value=10.0, step=0.5)
Lp = st.sidebar.number_input("Longueur panneau Lp (m)", min_value=2.0, max_value=20.0, value=5.0, step=0.5)

# Charges
st.sidebar.subheader("Charges (kN/m²)")
G = st.sidebar.number_input("Charge permanente G (kN/m²)", min_value=1.0, max_value=30.0, value=3.5, step=0.5)
Q = st.sidebar.number_input("Charge d'exploitation Q (kN/m²)", min_value=1.0, max_value=15.0, value=3.0, step=0.5)

# Portée
st.sidebar.subheader("Portée de la nervure")
orientation = st.sidebar.selectbox(
    "Orientation des nervures",
    ["Parallèles à la largeur Bp", "Parallèles à la longueur Lp"]
)

L = Bp if orientation == "Parallèles à la largeur Bp" else Lp
st.sidebar.info(f"Portée L = {L:.2f} m")

# Matériaux FIXES
st.sidebar.subheader("Matériaux (FIXES)")
st.sidebar.markdown("*Béton:* C25/30 (fck = 25 MPa)")
st.sidebar.markdown("*Acier:* FeE500")
st.sidebar.markdown("*Étriers:* HA8 e=20cm")

# ============================================
# DIMENSIONS EXACTES
# ============================================
ESPACEMENT_NERVURE = 0.60  # m
b_ame = 0.10  # m - Largeur de l'âme (10 cm)
h_ame = 0.16  # m - Hauteur de l'âme (16 cm)
b_talon = 0.02  # m - Largeur d'un talon (2 cm)
h_talon = 0.04  # m - Hauteur des talons (4 cm)
b_total_bas = b_ame + 2 * b_talon  # 0.14 m - Largeur totale en bas (14 cm)
h_total = h_ame + h_talon  # 0.20 m - Hauteur totale (20 cm)
enrobage = 0.03  # m

# ============================================
# CALCULS AUTOMATIQUES
# ============================================
st.header("📊 Résultats du calcul")

# 1. Nombre de nervures
N_nervures = ceil(Bp / ESPACEMENT_NERVURE)

# 2. Largeur tributaire
b_trib = Bp / N_nervures

# 3. Charge linéique
w = (G + Q) * b_trib  # kN/m

# 4. Moments
M_Ed = w * L**2 / 8  # kN.m
M_Ed_u = 1.4 * M_Ed  # kN.m

# 5. Dimensionnement acier
fck = 25  # MPa
fcd = 0.85 * fck / 1.5  # MPa
fyk = 500  # MPa (FeE500)
fyd = fyk / 1.15  # MPa

d = h_total - enrobage  # m

# Acier requis
M_Ed_u_Nmm = M_Ed_u * 1e6  # N.mm
As_req_mm2 = M_Ed_u_Nmm / (0.87 * fyd * 0.9 * d * 1000) if d > 0 else 0
As_req_cm2 = As_req_mm2 / 100

# 6. Choix ferraillage
diametres = [10, 12, 14, 16, 18, 20]
aires_barres = {10: 0.785, 12: 1.131, 14: 1.539, 16: 2.011, 18: 2.545, 20: 3.142}

meilleure_combinaison = None
for nb_barres in range(3, 6):
    for diam in diametres:
        As_prov = nb_barres * aires_barres[diam]
        if As_prov >= As_req_cm2:
            meilleure_combinaison = {
                'nb_barres': nb_barres,
                'diametre': diam,
                'As_prov': As_prov
            }
            break
    if meilleure_combinaison:
        break

if not meilleure_combinaison:
    meilleure_combinaison = {'nb_barres': 3, 'diametre': 20, 'As_prov': 3 * aires_barres[20]}

ratio = meilleure_combinaison['As_prov'] / As_req_cm2 if As_req_cm2 > 0 else 0

# ============================================
# AFFICHAGE RÉSULTATS
# ============================================
st.subheader("📋 Synthèse")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Nombre nervures", int(N_nervures))
    st.metric("Largeur tributaire", f"{b_trib:.3f} m")
with col2:
    st.metric("Charge linéique", f"{w:.3f} kN/m")
    st.metric("Moment ultime", f"{M_Ed_u:.2f} kN.m")
with col3:
    st.metric("Acier requis", f"{As_req_cm2:.2f} cm²")
    st.metric("Armature bas", f"{meilleure_combinaison['nb_barres']}Φ{meilleure_combinaison['diametre']}")
with col4:
    st.metric("Acier proposé", f"{meilleure_combinaison['As_prov']:.2f} cm²")
    st.metric("Ratio", f"{ratio:.2f}")

st.divider()

# ============================================
# SCHÉMAS COMPLETS ET PROFESSIONNELS
# ============================================
def create_complete_section():
    """Schéma complet de la section avec tous les détails"""
    fig, ax = plt.subplots(figsize=(10, 12))
    
    # Dimensions en cm
    b_ame_cm = b_ame * 100  # 10 cm
    h_ame_cm = h_ame * 100  # 16 cm
    b_talon_cm = b_talon * 100  # 2 cm
    h_talon_cm = h_talon * 100  # 4 cm
    b_total_cm = b_total_bas * 100  # 14 cm
    h_total_cm = h_total * 100  # 20 cm
    
    # Positionnement central
    x_center = 50
    y_base = 15
    
    # Coordonnées exactes
    x_ame_start = x_center - b_ame_cm/2
    x_talon_g_start = x_ame_start - b_talon_cm
    x_talon_d_end = x_ame_start + b_ame_cm + b_talon_cm
    
    y_talon_top = y_base + h_talon_cm
    y_total_top = y_base + h_total_cm
    
    # ===== DESSIN DE LA NERVURE =====
    # Fond avec dégradé visuel
    ax.fill_between([x_talon_g_start, x_talon_d_end], 
                   [y_base, y_base], [y_total_top, y_total_top],
                   color='#e8e8e8', alpha=0.9)
    
    # Contours avec épaisseur différente
    # Contour extérieur
    contour_x = [x_talon_g_start, x_talon_d_end, x_talon_d_end, 
                x_ame_start + b_ame_cm, x_ame_start + b_ame_cm,
                x_ame_start, x_ame_start, x_talon_g_start]
    contour_y = [y_base, y_base, y_talon_top, y_talon_top,
                y_total_top, y_total_top, y_talon_top, y_talon_top]
    
    ax.plot(contour_x + [contour_x[0]], contour_y + [contour_y[0]],
           color='#333333', linewidth=2.5, zorder=1)
    
    # Ligne de séparation entre talons et âme (légère)
    ax.plot([x_ame_start, x_ame_start], [y_base, y_talon_top], 
           color='#999999', linewidth=0.5, linestyle='--', alpha=0.5)
    ax.plot([x_ame_start + b_ame_cm, x_ame_start + b_ame_cm], [y_base, y_talon_top],
           color='#999999', linewidth=0.5, linestyle='--', alpha=0.5)
    
    # ===== ARMATURES BIEN CENTRÉES =====
    if meilleure_combinaison:
        diam_cm = meilleure_combinaison['diametre'] / 10
        nb_barres = meilleure_combinaison['nb_barres']
        
        # === ARMATURES EN BAS ===
        # Position Y: enrobage 2.5cm depuis le bas
        y_bas = y_base + 2.5 + diam_cm/2
        
        # Calcul position centrée DANS LE RECTANGLE INFÉRIEUR (14cm)
        # Les barres doivent être centrées dans les 14cm, pas dans toute la largeur
        total_width = b_total_cm  # 14 cm
        bar_width_total = nb_barres * diam_cm
        
        # Espacement égal de chaque côté
        side_space = (total_width - bar_width_total) / 2
        
        # Position de départ
        x_start = x_talon_g_start + side_space + diam_cm/2
        
        # Espacement entre barres
        space_between = (total_width - 2*side_space - nb_barres*diam_cm) / (nb_barres - 1) if nb_barres > 1 else 0
        
        # Dessin des barres avec effet 3D
        for i in range(nb_barres):
            x_pos = x_start + i * (diam_cm + space_between)
            
            # Cercle principal
            cercle = Circle((x_pos, y_bas), diam_cm/2,
                          facecolor='#ff4444', edgecolor='#cc0000', 
                          linewidth=1.5, zorder=5, alpha=0.9)
            ax.add_patch(cercle)
            
            # Reflet lumineux (petit cercle blanc)
            reflet = Circle((x_pos - diam_cm/6, y_bas + diam_cm/6), diam_cm/6,
                          facecolor='white', alpha=0.3, zorder=6)
            ax.add_patch(reflet)
        
        # === ARMATURE EN HAUT ===
        y_haut = y_total_top - 2.5 - 0.5
        x_haut = x_center  # Centrée dans l'âme
        
        cercle_haut = Circle((x_haut, y_haut), 0.5,
                           facecolor='#4444ff', edgecolor='#0000cc',
                           linewidth=1.5, zorder=5, alpha=0.9)
        ax.add_patch(cercle_haut)
        
        # Reflet pour armature haute
        reflet_haut = Circle((x_haut - 0.15, y_haut + 0.15), 0.15,
                           facecolor='white', alpha=0.3, zorder=6)
        ax.add_patch(reflet_haut)
    
    # ===== COTES AVEC FLÈCHES =====
    # Hauteur totale avec flèche double
    ax.annotate('', xy=(x_center-35, y_base), xytext=(x_center-35, y_total_top),
               arrowprops=dict(arrowstyle='<->', color='black', lw=1.5))
    ax.text(x_center-37, (y_base + y_total_top)/2, '20 cm',
           ha='right', va='center', rotation=90, fontsize=10, fontweight='bold',
           bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))
    
    # Largeur totale bas avec flèche
    ax.annotate('', xy=(x_talon_g_start, y_base-12), xytext=(x_talon_d_end, y_base-12),
               arrowprops=dict(arrowstyle='<->', color='black', lw=1.5))
    ax.text(x_center, y_base-15, '14 cm',
           ha='center', va='top', fontsize=10, fontweight='bold',
           bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))
    
    # Largeur âme avec flèche
    ax.annotate('', xy=(x_ame_start, y_base-25), xytext=(x_ame_start + b_ame_cm, y_base-25),
               arrowprops=dict(arrowstyle='<->', color='black', lw=1.5))
    ax.text(x_center, y_base-28, '10 cm',
           ha='center', va='top', fontsize=9,
           bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))
    
    # Hauteur âme avec flèche
    ax.annotate('', xy=(x_center+35, y_talon_top), xytext=(x_center+35, y_total_top),
               arrowprops=dict(arrowstyle='<->', color='black', lw=1.5))
    ax.text(x_center+37, (y_talon_top + y_total_top)/2, '16 cm',
           ha='left', va='center', rotation=90, fontsize=9,
           bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))
    
    # Hauteur talons avec flèche
    ax.annotate('', xy=(x_center+35, y_base), xytext=(x_center+35, y_talon_top),
               arrowprops=dict(arrowstyle='<->', color='black', lw=1.5))
    ax.text(x_center+37, (y_base + y_talon_top)/2, '4 cm',
           ha='left', va='center', rotation=90, fontsize=9,
           bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))
    
    # ===== ANNOTATIONS =====
    # Annotation âme
    ax.text(x_center, y_base + h_talon_cm + h_ame_cm/2, 'ÂME\n10×16 cm',
           ha='center', va='center', fontsize=9, fontweight='bold',
           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9))
    
    # Annotation talons
    ax.text(x_center - 8, y_base + h_talon_cm/2, 'TALON\n2×4 cm',
           ha='center', va='center', fontsize=8,
           bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.9))
    
    ax.text(x_center + 8, y_base + h_talon_cm/2, 'TALON\n2×4 cm',
           ha='center', va='center', fontsize=8,
           bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.9))
    
    # ===== LÉGENDE DES ARMATURES =====
    if meilleure_combinaison:
        legend_elements = [
            Line2D([0], [0], marker='o', color='w', 
                  markerfacecolor='#ff4444', markersize=10,
                  label=f'Armature tendue: {meilleure_combinaison["nb_barres"]}Φ{meilleure_combinaison["diametre"]}'),
            Line2D([0], [0], marker='o', color='w',
                  markerfacecolor='#4444ff', markersize=8,
                  label='Armature supérieure: 1Φ10')
        ]
        
        ax.legend(handles=legend_elements, loc='lower center',
                 bbox_to_anchor=(0.5, -0.05), ncol=2, fontsize=9,
                 frameon=True, fancybox=True, shadow=True)
    
    # ===== TITRE ET INFORMATIONS =====
    ax.text(x_center, y_total_top + 15, 'SECTION TRANSVERSALE - NERVURE EN T RENVERSÉ',
           ha='center', va='bottom', fontsize=13, fontweight='bold',
           bbox=dict(boxstyle='round,pad=0.5', facecolor='#f0f0f0', alpha=0.9))
    
    # Informations de calcul
    info_text = f"M_Ed = {M_Ed_u:.1f} kN.m  |  Acier = {meilleure_combinaison['As_prov']:.1f} cm²  |  Ratio = {ratio:.2f}"
    ax.text(x_center, y_base - 35, info_text,
           ha='center', va='top', fontsize=9,
           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9))
    
    # ===== CONFIGURATION FINALE =====
    ax.set_xlim(x_center - 50, x_center + 50)
    ax.set_ylim(y_base - 40, y_total_top + 20)
    ax.set_aspect('equal')
    ax.axis('off')
    
    plt.tight_layout()
    return fig

def create_complete_longitudinal():
    """Schéma longitudinal complet avec tous les détails"""
    fig, ax = plt.subplots(figsize=(14, 8))
    
    L_cm = L * 100
    y_base = 25
    section_height = h_total * 100
    y_top = y_base + section_height
    
    # Facteur d'échelle adaptatif
    scale_factor = min(1.0, 800 / L_cm) if L_cm > 0 else 1.0
    scaled_height = section_height * scale_factor
    y_top_scaled = y_base + scaled_height
    
    # ===== DESSIN DE LA POUTRE =====
    # Poutre avec effet de profondeur
    ax.fill_between([0, L_cm], y_base, y_top_scaled,
                   color='#f0f0f0', alpha=0.9, edgecolor='#333', linewidth=2)
    
    # Ligne médiane pour effet 3D
    ax.plot([0, L_cm], [(y_base + y_top_scaled)/2, (y_base + y_top_scaled)/2],
           color='#ccc', linewidth=0.5, linestyle='--', alpha=0.5)
    
    # ===== ARMATURES LONGITUDINALES =====
    if meilleure_combinaison:
        # Armature inférieure
        y_inf = y_base + scaled_height * 0.2
        line_width_inf = 2 + meilleure_combinaison['diametre']/15
        
        ax.plot([L_cm*0.1, L_cm*0.9], [y_inf, y_inf],
               color='#ff4444', linewidth=line_width_inf, 
               solid_capstyle='round',
               label=f'Armature inférieure: {meilleure_combinaison["nb_barres"]}Φ{meilleure_combinaison["diametre"]}')
        
        # Armature supérieure
        y_sup = y_top_scaled - scaled_height * 0.2
        ax.plot([L_cm*0.1, L_cm*0.9], [y_sup, y_sup],
               color='#4444ff', linewidth=2.5, solid_capstyle='round',
               label='Armature supérieure: 1Φ10')
        
        # Ancrages aux extrémités (coudes)
        for x in [L_cm*0.1, L_cm*0.9]:
            ax.plot([x-10, x, x], [y_inf, y_inf, y_inf+5], 
                   color='#ff4444', linewidth=1, linestyle=':', alpha=0.5)
            ax.plot([x, x+10, x+10], [y_sup-5, y_sup-5, y_sup], 
                   color='#4444ff', linewidth=1, linestyle=':', alpha=0.5)
    
    # ===== ÉTRIERS =====
    etrier_spacing = 20  # cm
    num_etriers = int(L_cm / etrier_spacing)
    
    for i in range(1, num_etriers):
        x_pos = i * etrier_spacing
        if L_cm*0.15 < x_pos < L_cm*0.85:
            # Étrier principal
            ax.plot([x_pos, x_pos], [y_base+3, y_top_scaled-3],
                   color='#00aa44', linewidth=1.5, alpha=0.8)
            
            # Têtes d'étrier
            ax.plot([x_pos-2, x_pos+2], [y_base+3, y_base+3],
                   color='#00aa44', linewidth=1.5, alpha=0.8)
            ax.plot([x_pos-2, x_pos+2], [y_top_scaled-3, y_top_scaled-3],
                   color='#00aa44', linewidth=1.5, alpha=0.8)
            
            # Annotation périodique
            if i % 5 == 0:
                ax.text(x_pos, y_base-5, 'HA6',
                       ha='center', va='top', fontsize=8, color='#008833', fontweight='bold')
                ax.text(x_pos, y_base-8, 'e=20cm',
                       ha='center', va='top', fontsize=7, color='#008833')
    
    # ===== APPRUIS =====
    appui_width = max(15, L_cm * 0.03)
    appui_height = 8
    
    # Appui gauche avec effet 3D
    appui_g = FancyBboxPatch((-appui_width/2, y_base-appui_height),
                           appui_width, appui_height,
                           boxstyle="round,pad=0.1",
                           facecolor='#888888', edgecolor='#555555',
                           linewidth=1.5, alpha=0.9)
    ax.add_patch(appui_g)
    
    # Appui droit
    appui_d = FancyBboxPatch((L_cm-appui_width/2, y_base-appui_height),
                           appui_width, appui_height,
                           boxstyle="round,pad=0.1",
                           facecolor='#888888', edgecolor='#555555',
                           linewidth=1.5, alpha=0.9)
    ax.add_patch(appui_d)
    
    # Textes appuis
    ax.text(0, y_base-appui_height-3, 'APPUI',
           ha='center', va='top', fontsize=10, fontweight='bold', color='#333')
    ax.text(L_cm, y_base-appui_height-3, 'APPUI',
           ha='center', va='top', fontsize=10, fontweight='bold', color='#333')
    
    # ===== COURBE DE MOMENT (FLÈCHE) =====
    x_moment = np.linspace(0, L_cm, 100)
    moment_max = scaled_height * 0.4
    y_moment = y_base + scaled_height/2 + moment_max * np.sin(np.pi * x_moment / L_cm)
    
    ax.plot(x_moment, y_moment, color='#9933cc', linewidth=2, linestyle='--',
           alpha=0.7, label='Courbe de moment')
    
    # Flèche maximum
    ax.annotate('Flèche max', xy=(L_cm/2, y_base + scaled_height/2 + moment_max),
               xytext=(L_cm/2, y_base + scaled_height/2 + moment_max + 10),
               ha='center', va='bottom', fontsize=9, color='#9933cc',
               arrowprops=dict(arrowstyle='->', color='#9933cc', alpha=0.7))
    
    # ===== COTE DE PORTÉE =====
    cote_y = y_base - 20
    ax.annotate('', xy=(0, cote_y), xytext=(L_cm, cote_y),
               arrowprops=dict(arrowstyle='<->', color='black', lw=1.5))
    
    ax.text(L_cm/2, cote_y-3, f'PORTÉE L = {L:.2f} m',
           ha='center', va='top', fontsize=12, fontweight='bold',
           bbox=dict(boxstyle='round,pad=0.4', facecolor='white', alpha=0.9))
    
    # ===== TITRE ET INFORMATIONS =====
    ax.text(L_cm/2, y_top_scaled + 15, 'VUE LONGITUDINALE - NERVURE EN T RENVERSÉ',
           ha='center', va='bottom', fontsize=14, fontweight='bold', color='#333')
    
    # Informations techniques
    info_y = y_base - 15
    ax.text(L_cm/4, info_y, f'Section: 14×20 cm',
           ha='center', va='top', fontsize=10, fontweight='bold')
    ax.text(L_cm/2, info_y, f'M_Ed = {M_Ed_u:.1f} kN.m',
           ha='center', va='top', fontsize=10, fontweight='bold')
    ax.text(3*L_cm/4, info_y, f'Béton C25/30',
           ha='center', va='top', fontsize=10, fontweight='bold')
    
    # ===== LÉGENDE =====
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05),
             ncol=3, fontsize=10, framealpha=0.9, frameon=True,
             fancybox=True, shadow=True)
    
    # ===== CONFIGURATION FINALE =====
    margin = max(30, L_cm * 0.05)
    ax.set_xlim(-margin, L_cm + margin)
    ax.set_ylim(y_base - 30, y_top_scaled + 20)
    ax.set_aspect('auto')
    ax.axis('off')
    
    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    return fig

# ============================================
# AFFICHAGE SCHÉMAS
# ============================================
st.header("📐 Schémas techniques")

col_s1, col_s2 = st.columns(2)
with col_s1:
    st.subheader("Section transversale")
    fig_section = create_complete_section()
    st.pyplot(fig_section)

with col_s2:
    st.subheader("Vue longitudinale")
    fig_longitudinal = create_complete_longitudinal()
    st.pyplot(fig_longitudinal)

# ============================================
# GÉNÉRATION PDF PROFESSIONNEL
# ============================================
def create_professional_pdf():
    """PDF avec gestion d'échelle et présentation professionnelle"""
    buffer = io.BytesIO()
    
    # Créer un document avec des pages séparées
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                          rightMargin=1.5*cm, leftMargin=1.5*cm,
                          topMargin=1.5*cm, bottomMargin=1.5*cm)
    
    story = []
    styles = getSampleStyleSheet()
    
    # Styles personnalisés
    title_style = ParagraphStyle(
        'MainTitle',
        parent=styles['Title'],
        fontSize=16,
        alignment=1,
        spaceAfter=20,
        fontName='Helvetica-Bold'
    )
    
    section_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=12,
        spaceBefore=15,
        spaceAfter=10,
        fontName='Helvetica-Bold'
    )
    
    temp_files = []
    
    try:
        # ===== PAGE 1: RÉSULTATS =====
        story.append(Paragraph("RAPPORT DE CALCUL - DALLE NERVURÉE", title_style))
        story.append(Paragraph("Norme: Eurocode 2 (méthode simplifiée)", 
                              ParagraphStyle('Subtitle', parent=styles['Normal'], 
                                           fontSize=10, alignment=1, spaceAfter=25)))
        
        # Tableau des paramètres
        story.append(Paragraph("1. PARAMÈTRES DU PROJET", section_style))
        
        data_params = [
            ["Paramètre", "Valeur", "Unité"],
            ["Largeur panneau Bp", f"{Bp:.2f}", "m"],
            ["Longueur panneau Lp", f"{Lp:.2f}", "m"],
            ["Orientation", orientation.replace("Parallèles à ", ""), ""],
            ["Portée L", f"{L:.2f}", "m"],
            ["Charge permanente G", f"{G:.2f}", "kN/m²"],
            ["Charge exploitation Q", f"{Q:.2f}", "kN/m²"],
            ["Béton", "C25/30 (fck=25 MPa)", ""],
            ["Acier", "FeE500", ""],
        ]
        
        table_params = Table(data_params, colWidths=[6*cm, 4*cm, 2*cm])
        table_params.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        story.append(table_params)
        story.append(Spacer(1, 0.8*cm))
        
        # Tableau des résultats
        story.append(Paragraph("2. RÉSULTATS DES CALCULS", section_style))
        
        data_res = [
            ["Paramètre", "Valeur", "Unité"],
            ["Nombre de nervures", f"{int(N_nervures)}", ""],
            ["Largeur tributaire", f"{b_trib:.3f}", "m"],
            ["Charge linéique w", f"{w:.3f}", "kN/m"],
            ["Moment M_Ed", f"{M_Ed:.3f}", "kN.m"],
            ["Moment ultime M_Ed,u", f"{M_Ed_u:.3f}", "kN.m"],
            ["fcd", f"{fcd:.1f}", "MPa"],
            ["fyd", f"{fyd:.1f}", "MPa"],
            ["Acier requis", f"{As_req_cm2:.2f}", "cm²"],
            ["Acier proposé", f"{meilleure_combinaison['As_prov']:.2f}", "cm²"],
            ["Armature inférieure", f"{meilleure_combinaison['nb_barres']} Φ{meilleure_combinaison['diametre']}", "mm"],
            ["Armature supérieure", "1 Φ10", "mm"],
            ["Étriers", "HA8 e=20 cm", ""],
            ["Ratio As,prov/As,req", f"{ratio:.2f}", ""],
        ]
        
        table_res = Table(data_res, colWidths=[6*cm, 4*cm, 2*cm])
        table_res.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2ecc71')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        story.append(table_res)
        
        # ===== PAGE 2: SECTION TRANSVERSALE (MÊME QUE L'INTERFACE) =====
        story.append(PageBreak())
        
        with tempfile.NamedTemporaryFile(suffix='_section_pdf.png', delete=False) as f1:
            # Utiliser EXACTEMENT la même fonction que pour l'interface
            fig_section = create_complete_section()
            
            # Ajuster légèrement la taille pour le PDF
            fig_section.set_size_inches(13, 15)  # LÉGÈREMENT PLUS GRAND
            
            # Sauvegarder
            fig_section.savefig(f1.name, dpi=300, bbox_inches='tight', pad_inches=0.2)
            temp_files.append(f1.name)
            plt.close(fig_section)
            
            # Ajouter au PDF
            story.append(Paragraph("SECTION TRANSVERSALE - NERVURE EN T RENVERSÉ", 
                                  section_style))
            story.append(Spacer(1, 0.3*cm))
            
            # Image avec largeur OPTIMISÉE (20cm au lieu de 25cm original, 16cm précédent)
            img_width = 20*cm  # OPTIMISÉ : +4cm par rapport à précédent (16cm → 20cm)
            img_height = 23*cm  # Hauteur proportionnelle
            
            # Créer un tableau pour centrer l'image
            centered_table = Table([[RLImage(f1.name, width=img_width, height=img_height)]], 
                                 colWidths=[18*cm])
            centered_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))
            story.append(centered_table)
            
            # Légende
            if meilleure_combinaison:
                legende = f"Armature tendue: {meilleure_combinaison['nb_barres']}Φ{meilleure_combinaison['diametre']} (rouge) | Armature supérieure: 1Φ10 (bleu) | Étriers: HA8 e=20 cm"
                story.append(Spacer(1, 0.2*cm))
                story.append(Paragraph(legende, 
                                      ParagraphStyle('Legende', parent=styles['Normal'], 
                                                   fontSize=9, alignment=1)))
        
        # ===== PAGE 3: VUE LONGITUDINALE =====
        story.append(PageBreak())
        
        with tempfile.NamedTemporaryFile(suffix='_long_pdf.png', delete=False) as f2:
            # Utiliser EXACTEMENT la même fonction que pour l'interface
            fig_longitudinal = create_complete_longitudinal()
            fig_longitudinal.set_size_inches(16, 9)  # LÉGÈREMENT PLUS GRAND
            fig_longitudinal.savefig(f2.name, dpi=300, bbox_inches='tight', pad_inches=0.2)
            temp_files.append(f2.name)
            plt.close(fig_longitudinal)
            
            story.append(Paragraph("VUE LONGITUDINALE", section_style))
            story.append(Spacer(1, 0.3*cm))
            
            # Image centrée avec largeur OPTIMISÉE (20cm au lieu de 18cm précédent)
            img_width = min(20*cm, max(16*cm, L * 2.8 * cm))  # OPTIMISÉ : +2cm
            img_height = 11*cm  # Hauteur proportionnelle
            
            centered_table = Table([[RLImage(f2.name, width=img_width, height=img_height)]], 
                                 colWidths=[18*cm])
            centered_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(centered_table)
        
        # ===== PAGE 4: NOTES TECHNIQUES =====
        story.append(PageBreak())
        
        story.append(Paragraph("CARACTÉRISTIQUES TECHNIQUES", section_style))
        story.append(Spacer(1, 0.5*cm))
        
        notes_data = [
            ["DIMENSIONS", "VALEUR"],
            ["Hauteur totale de la nervure", "20 cm"],
            ["Largeur totale en bas", "14 cm"],
            ["Largeur de l'âme", "10 cm"],
            ["Hauteur de l'âme", "16 cm"],
            ["Largeur d'un talon", "2 cm"],
            ["Hauteur des talons", "4 cm"],
            ["Entrevois", "60 cm d'entraxe"],
            ["Enrobage nominal", "3 cm"],
        ]
        
        table_notes = Table(notes_data, colWidths=[8*cm, 4*cm])
        table_notes.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ]))
        story.append(table_notes)
        story.append(Spacer(1, 0.8*cm))
        
        story.append(Paragraph("INFORMATIONS DE CALCUL", section_style))
        
        notes_list = [
            f"• Calcul selon Eurocode 2 (méthode simplifiée)",
            f"• Combinaison fondamentale: 1.35G + 1.5Q",
            f"• Coefficient de sécurité partiel béton: γc = 1.5",
            f"• Coefficient de sécurité partiel acier: γs = 1.15",
            f"• Hauteur utile: d = h - enrobage = 20 - 3 = 17 cm",
            f"• Contrainte de compression béton: fcd = 0.85 × fck / γc = {fcd:.1f} MPa",
            f"• Contrainte de traction acier: fyd = fyk / γs = {fyd:.1f} MPa",
            f"• Armature inférieure: {meilleure_combinaison['nb_barres']}Φ{meilleure_combinaison['diametre']}",
            f"• Armature supérieure: 1Φ10 • Étriers: HA8 espacés de 20 cm",
            f"• M_Ed = {M_Ed_u:.1f} kN.m • Acier proposé: {meilleure_combinaison['As_prov']:.1f} cm²",
            f"• Ratio As,prov/As,req = {ratio:.2f}",
            f"• Validation par ingénieur structure recommandée avant exécution"
        ]
        
        for note in notes_list:
            story.append(Paragraph(note, ParagraphStyle('Bullet', 
                                                      parent=styles['Normal'], 
                                                      fontSize=9,
                                                      leftIndent=20)))
            story.append(Spacer(1, 0.1*cm))
        
        # Espace pour signature
        story.append(Spacer(1, 2*cm))
        story.append(Paragraph("_" * 50, ParagraphStyle('Line', parent=styles['Normal'], alignment=1)))
        story.append(Paragraph("Signature / Cachet", 
                              ParagraphStyle('Signature', parent=styles['Normal'], 
                                           fontSize=10, alignment=1, spaceBefore=5)))
        
        # Footer avec date
        story.append(Spacer(1, 1*cm))
        date_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
        story.append(Paragraph(f"Document généré le {date_str}", 
                              ParagraphStyle('Footer', parent=styles['Normal'], 
                                           fontSize=8, alignment=1, textColor=colors.grey)))
        
        doc.build(story)
        plt.close('all')
        
        return buffer.getvalue()
        
    finally:
        for f in temp_files:
            try:
                if os.path.exists(f):
                    os.unlink(f)
            except:
                pass
    """PDF avec gestion d'échelle et présentation professionnelle"""
    buffer = io.BytesIO()
    
    # Créer un document avec des pages séparées
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                          rightMargin=1.5*cm, leftMargin=1.5*cm,
                          topMargin=1.5*cm, bottomMargin=1.5*cm)
    
    story = []
    styles = getSampleStyleSheet()
    
    # Styles personnalisés
    title_style = ParagraphStyle(
        'MainTitle',
        parent=styles['Title'],
        fontSize=16,
        alignment=1,
        spaceAfter=20,
        fontName='Helvetica-Bold'
    )
    
    section_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=12,
        spaceBefore=15,
        spaceAfter=10,
        fontName='Helvetica-Bold'
    )
    
    temp_files = []
    
    try:
        # ===== PAGE 1: RÉSULTATS =====
        story.append(Paragraph("RAPPORT DE CALCUL - DALLE NERVURÉE", title_style))
        story.append(Paragraph("Norme: Eurocode 2 (méthode simplifiée)", 
                              ParagraphStyle('Subtitle', parent=styles['Normal'], 
                                           fontSize=10, alignment=1, spaceAfter=25)))
        
        # Tableau des paramètres
        story.append(Paragraph("1. PARAMÈTRES DU PROJET", section_style))
        
        data_params = [
            ["Paramètre", "Valeur", "Unité"],
            ["Largeur panneau Bp", f"{Bp:.2f}", "m"],
            ["Longueur panneau Lp", f"{Lp:.2f}", "m"],
            ["Orientation", orientation.replace("Parallèles à ", ""), ""],
            ["Portée L", f"{L:.2f}", "m"],
            ["Charge permanente G", f"{G:.2f}", "kN/m²"],
            ["Charge exploitation Q", f"{Q:.2f}", "kN/m²"],
            ["Béton", "C25/30 (fck=25 MPa)", ""],
            ["Acier", "FeE500", ""],
        ]
        
        table_params = Table(data_params, colWidths=[6*cm, 4*cm, 2*cm])
        table_params.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        story.append(table_params)
        story.append(Spacer(1, 0.8*cm))
        
        # Tableau des résultats
        story.append(Paragraph("2. RÉSULTATS DES CALCULS", section_style))
        
        data_res = [
            ["Paramètre", "Valeur", "Unité"],
            ["Nombre de nervures", f"{int(N_nervures)}", ""],
            ["Largeur tributaire", f"{b_trib:.3f}", "m"],
            ["Charge linéique w", f"{w:.3f}", "kN/m"],
            ["Moment M_Ed", f"{M_Ed:.3f}", "kN.m"],
            ["Moment ultime M_Ed,u", f"{M_Ed_u:.3f}", "kN.m"],
            ["fcd", f"{fcd:.1f}", "MPa"],
            ["fyd", f"{fyd:.1f}", "MPa"],
            ["Acier requis", f"{As_req_cm2:.2f}", "cm²"],
            ["Acier proposé", f"{meilleure_combinaison['As_prov']:.2f}", "cm²"],
            ["Armature inférieure", f"{meilleure_combinaison['nb_barres']} Φ{meilleure_combinaison['diametre']}", "mm"],
            ["Armature supérieure", "1 Φ10", "mm"],
            ["Étriers", "HA8 e=20 cm", ""],
            ["Ratio As,prov/As,req", f"{ratio:.2f}", ""],
        ]
        
        table_res = Table(data_res, colWidths=[6*cm, 4*cm, 2*cm])
        table_res.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2ecc71')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        story.append(table_res)
        
        # ===== PAGE 2: SECTION TRANSVERSALE (MÊME QUE L'INTERFACE) =====
        story.append(PageBreak())
        
        with tempfile.NamedTemporaryFile(suffix='_section_pdf.png', delete=False) as f1:
            # Utiliser EXACTEMENT la même fonction que pour l'interface
            fig_section = create_complete_section()
            
            # JUSTE ajuster la taille pour le PDF
            fig_section.set_size_inches(12, 14)  # Un peu plus large pour garder les proportions
            
            # Sauvegarder avec compression optimale
            fig_section.savefig(f1.name, dpi=300, bbox_inches='tight', pad_inches=0.3)
            temp_files.append(f1.name)
            plt.close(fig_section)
            
            # Ajouter au PDF
            story.append(Paragraph("SECTION TRANSVERSALE - NERVURE EN T RENVERSÉ", 
                                  section_style))
            story.append(Spacer(1, 0.5*cm))
            
            # Image avec largeur réduite et centrée
            img_width = 16*cm  # Largeur réduite (était 25cm)
            img_height = 18*cm  # Hauteur proportionnelle
            
            # Créer un tableau pour centrer l'image
            centered_table = Table([[RLImage(f1.name, width=img_width, height=img_height)]], 
                                 colWidths=[18*cm])
            centered_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))
            story.append(centered_table)
            
            # Légende
            if meilleure_combinaison:
                legende = f"Armature tendue: {meilleure_combinaison['nb_barres']}Φ{meilleure_combinaison['diametre']} (rouge) | Armature supérieure: 1Φ10 (bleu) | Étriers: HA8 e=20 cm"
                story.append(Spacer(1, 0.3*cm))
                story.append(Paragraph(legende, 
                                      ParagraphStyle('Legende', parent=styles['Normal'], 
                                                   fontSize=9, alignment=1)))
        
        # ===== PAGE 3: VUE LONGITUDINALE =====
        story.append(PageBreak())
        
        with tempfile.NamedTemporaryFile(suffix='_long_pdf.png', delete=False) as f2:
            # Utiliser EXACTEMENT la même fonction que pour l'interface
            fig_longitudinal = create_complete_longitudinal()
            fig_longitudinal.set_size_inches(14, 8)
            fig_longitudinal.savefig(f2.name, dpi=300, bbox_inches='tight')
            temp_files.append(f2.name)
            plt.close(fig_longitudinal)
            
            story.append(Paragraph("VUE LONGITUDINALE", section_style))
            story.append(Spacer(1, 0.5*cm))
            
            # Image centrée avec largeur adaptative
            img_width = min(18*cm, max(14*cm, L * 2.5 * cm))
            img_height = 10*cm
            
            centered_table = Table([[RLImage(f2.name, width=img_width, height=img_height)]], 
                                 colWidths=[18*cm])
            centered_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(centered_table)
        
        # ===== PAGE 4: NOTES TECHNIQUES =====
        story.append(PageBreak())
        
        story.append(Paragraph("CARACTÉRISTIQUES TECHNIQUES", section_style))
        story.append(Spacer(1, 0.5*cm))
        
        notes_data = [
            ["DIMENSIONS", "VALEUR"],
            ["Hauteur totale de la nervure", "20 cm"],
            ["Largeur totale en bas", "14 cm"],
            ["Largeur de l'âme", "10 cm"],
            ["Hauteur de l'âme", "16 cm"],
            ["Largeur d'un talon", "2 cm"],
            ["Hauteur des talons", "4 cm"],
            ["Entrevois", "60 cm d'entraxe"],
            ["Enrobage nominal", "3 cm"],
        ]
        
        table_notes = Table(notes_data, colWidths=[8*cm, 4*cm])
        table_notes.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ]))
        story.append(table_notes)
        story.append(Spacer(1, 0.8*cm))
        
        story.append(Paragraph("INFORMATIONS DE CALCUL", section_style))
        
        notes_list = [
            f"• Calcul selon Eurocode 2 (méthode simplifiée)",
            f"• Combinaison fondamentale: 1.35G + 1.5Q",
            f"• Coefficient de sécurité partiel béton: γc = 1.5",
            f"• Coefficient de sécurité partiel acier: γs = 1.15",
            f"• Hauteur utile: d = h - enrobage = 20 - 3 = 17 cm",
            f"• Contrainte de compression béton: fcd = 0.85 × fck / γc = {fcd:.1f} MPa",
            f"• Contrainte de traction acier: fyd = fyk / γs = {fyd:.1f} MPa",
            f"• Armature inférieure: {meilleure_combinaison['nb_barres']}Φ{meilleure_combinaison['diametre']}",
            f"• Armature supérieure: 1Φ10 • Étriers: HA8 espacés de 20 cm",
            f"• M_Ed = {M_Ed_u:.1f} kN.m • Acier proposé: {meilleure_combinaison['As_prov']:.1f} cm²",
            f"• Ratio As,prov/As,req = {ratio:.2f}",
            f"• Validation par ingénieur structure recommandée avant exécution"
        ]
        
        for note in notes_list:
            story.append(Paragraph(note, ParagraphStyle('Bullet', 
                                                      parent=styles['Normal'], 
                                                      fontSize=9,
                                                      leftIndent=20)))
            story.append(Spacer(1, 0.1*cm))
        
        # Espace pour signature
        story.append(Spacer(1, 2*cm))
        story.append(Paragraph("_" * 50, ParagraphStyle('Line', parent=styles['Normal'], alignment=1)))
        story.append(Paragraph("Signature / Cachet", 
                              ParagraphStyle('Signature', parent=styles['Normal'], 
                                           fontSize=10, alignment=1, spaceBefore=5)))
        
        # Footer avec date
        story.append(Spacer(1, 1*cm))
        date_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
        story.append(Paragraph(f"Document généré le {date_str}", 
                              ParagraphStyle('Footer', parent=styles['Normal'], 
                                           fontSize=8, alignment=1, textColor=colors.grey)))
        
        doc.build(story)
        plt.close('all')
        
        return buffer.getvalue()
        
    finally:
        for f in temp_files:
            try:
                if os.path.exists(f):
                    os.unlink(f)
            except:
                pass
# ============================================
# EXPORT PDF
# ============================================
st.divider()
st.header("📤 Export du rapport")

if st.button("📄 Générer le rapport PDF complet", type="primary", use_container_width=True):
    with st.spinner("Génération du rapport professionnel..."):
        try:
            pdf_bytes = create_professional_pdf()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"Rapport_Dalle_{Bp}x{Lp}m_{timestamp}.pdf"
            
            st.download_button(
                label="⬇️ Télécharger le rapport PDF",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                use_container_width=True
            )
            
            st.success("✅ Rapport PDF généré avec succès!")
            
        except Exception as e:
            st.error(f"❌ Erreur: {str(e)}")

# ============================================
# FOOTER
# ============================================
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.85em; padding: 10px;'>
    Outil de calcul technique - Dalle nervurée selon EC2 simplifié<br>
    Version finale • Pour usage préliminaire • © 2024
</div>
""", unsafe_allow_html=True)