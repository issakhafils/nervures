# 🏗️ Calcul de Dalle Nervurée - EC2 Simplifié

Une application web interactive développée avec **Streamlit** permettant le prédimensionnement et le calcul automatique du ferraillage d'une dalle nervurée (poutre en T renversé) selon l'**Eurocode 2 (NF EN 1992-1-1)**.

L'outil génère également des schémas techniques haute définition (coupe transversale et vue longitudinale) et exporte un **rapport d'ingénierie complet au format PDF**.

---

## 🚀 Fonctionnalités

- **Saisie interactive des paramètres :** Ajustement en temps réel des dimensions du panneau de dalle et des charges appliquées.
- **Calcul automatique des charges tributaires :** Détermination dynamique de la largeur d'influence par nervure et des charges linéiques de calcul.
- **Optimisation des armatures :** Algorithme de choix automatique de la meilleure combinaison de barres d'acier (HA) pour satisfaire la section requise au sens de l'ELU.
- **Visualisations graphiques avancées :** 
  - Coupe transversale cotée détaillée de la nervure avec positionnement précis des aciers longitudinaux et de construction.
  - Vue longitudinale dynamique montrant la portée, les appuis, les aciers et le diagramme enveloppe simplifié du moment fléchissant.
- **Export PDF professionnel :** Génération d'une note de calcul structurée sur plusieurs pages incluant tableaux récapitulatifs, schémas graphiques intégrés et zone de visa/signature.

---

## 🧮 Hypothèses de calcul & Matériaux

L'application repose sur une approche simplifiée de calcul des sections en T selon l'**Eurocode 2** :
- **Béton :** Classe `C25/30` fixe ($f_{ck} = 25\text{ MPa}$, $f_{cd} = 14.17\text{ MPa}$).
- **Acier de renforcement :** Nuance de haute ductilité `FeE500` ($f_{yk} = 500\text{ MPa}$, $f_{yd} = 434.78\text{ MPa}$).
- **Géométrie de la nervure :** Section standard en T renversé (Épaisseur totale de $20\text{ cm}$ avec âme de $10\times16\text{ cm}$ et talons de $2\times4\text{ cm}$).
- **Armatures transversales :** Cadres/étriers fixes en $\Phi6$ avec un espacement régulier de $20\text{ cm}$.
- **Enrobage nominal :** $c_{nom} = 3.0\text{ cm}$ pour répondre aux exigences de durabilité standard.

---

## 🛠️ Installation et Configuration

### 1. Prérequis
Assurez-vous d'avoir Python 3.8 ou une version ultérieure installée sur votre machine.

### 2. Cloner le projet ou copier le code
Créez un fichier nommé `app.py` et collez-y le code de l'application.

### 3. Installer les dépendances
Installez les packages Python requis à l'aide de `pip` :

```bash
pip install streamlit numpy pandas matplotlib reportlab
```

---

## 💻 Utilisation

Pour lancer l'application sur votre serveur local, exécutez la commande suivante dans votre terminal :

```bash
streamlit run app.py
```

L'application s'ouvrira automatiquement dans votre navigateur par défaut à l'adresse `http://localhost:8501`.

1. **Panneau Latéral :** Modifiez la largeur ($B_p$) et la longueur ($L_p$) du panneau, ainsi que les charges permanentes ($G$) et d'exploitation ($Q$). Choisissez l'orientation des nervures pour basculer automatiquement la portée $L$.
2. **Tableau de Synthèse :** Visualisez instantanément le nombre de nervures requis, le moment ultime ($M_{Ed,u}$), la section d'acier théorique calculée et la combinaison commerciale optimale proposée.
3. **Schémas Techniques :** Examinez les plans de ferraillage générés dynamiquement par `matplotlib`.
4. **Téléchargement :** Utilisez le bouton de génération pour obtenir votre rapport PDF prêt pour l'impression ou l'archivage de projet.

---

## 📁 Structure du Code

- **`create_complete_section()` :** Construit la géométrie vectorielle précise de la coupe de la nervure avec une disposition graphique équilibrée des barres d'acier tendues.
- **`create_complete_longitudinal()` :** Génère la vue en élévation de la poutre sur ses appuis simples en appliquant un facteur d'échelle adaptatif selon la portée.
- **`create_professional_pdf()` :** Assemble l'ensemble des données entrées/sorties et des rendus d'images dans un flux `ReportLab` hautement formalisé (Page de garde/Paramètres, Planches graphiques, Spécifications techniques et Clôture).

---

## ⚠️ Avertissement
*Cet outil est une application de prédimensionnement basée sur une méthode simplifiée. Les calculs doivent être vérifiés et validés par un ingénieur en structures qualifié avant toute mise en œuvre ou exécution sur chantier.*
