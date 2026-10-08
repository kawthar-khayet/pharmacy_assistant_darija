"""Composeur : des resultats des outils a des phrases courtes.

Chaque fonction recoit la sortie d'un outil (nlp/outils/) et renvoie un Bloc :
  tete  : ce qui repond a la question (toujours affiche) ;
  liste : le detail d'une liste de pharmacies, que l'interface remplace par
          des fiches (la version courte de la reponse l'omet) ;
  pied  : une remarque apres la liste (garde, distances approximatives...).
On ne redige que ce qui a ete demande, jamais toute la fiche du medicament.
"""
import re
from dataclasses import dataclass, field

from nlp.reponse.phrases import t

# Au-dela, une liste de villes devient illisible dans un chat.
MAX_VILLES = 6


@dataclass
class Bloc:
    tete: list[str] = field(default_factory=list)
    liste: list[str] = field(default_factory=list)
    pied: list[str] = field(default_factory=list)

    def texte(self, court: bool = False) -> str:
        lignes = self.tete + ([] if court else self.liste) + self.pied
        return "\n".join(l for l in lignes if l)


def phrase(langue: str, cle: str, **params) -> Bloc:
    return Bloc([t(langue, cle, **params)])


# --- Mise en forme ------------------------------------------------------------

def prix_txt(valeur: float, langue: str) -> str:
    """12.5 -> "12,50 DH" en francais, "12.50 درهم" en arabe."""
    chiffre = f"{valeur:.2f}"
    if langue == "fr":
        chiffre = chiffre.replace(".", ",")
    return f"{chiffre} {t(langue, 'dh')}"


def nombre_txt(valeur: float, langue: str) -> str:
    texte = f"{valeur:g}"
    return texte.replace(".", ",") if langue == "fr" else texte


def duree_txt(jours: int, langue: str) -> str:
    return t(langue, "jour") if jours == 1 else t(langue, "jours", n=jours)


def telephone_txt(tel) -> str | None:
    """"539813017" -> "0539 81 30 17" ; un numero illisible est rendu tel quel."""
    if not tel:
        return None
    chiffres = re.sub(r"\D", "", str(tel))
    if chiffres.startswith("212"):
        chiffres = "0" + chiffres[3:]
    elif len(chiffres) == 9 and chiffres[0] in "5678":
        chiffres = "0" + chiffres
    if len(chiffres) == 10 and chiffres.startswith("0"):
        return f"{chiffres[:4]} {chiffres[4:6]} {chiffres[6:8]} {chiffres[8:]}"
    return str(tel)


def distance_txt(km: float, langue: str) -> str:
    if km < 1:
        return f"{round(km * 1000 / 50) * 50 or 50} m"
    return f"{nombre_txt(round(km, 1), langue)} km"


def nom_txt(nom) -> str:
    """"AUGMENTIN" -> "Augmentin" : les bases ecrivent tout en capitales."""
    nom = str(nom or "")
    return nom.title() if nom.isupper() else nom


def minuscule_initiale(texte: str) -> str:
    """"Fièvre légère, moins de 38,5 °C" -> "fièvre légère, moins de 38,5 °C"."""
    return texte[:1].lower() + texte[1:]


def presentation_txt(dosage, forme) -> str:
    return " ".join(str(x).lower() for x in (dosage, forme) if x).strip()


def molecule_txt(dci: str) -> str:
    """"ALGINATE DE SODIUM // BICARBONATE DE SODIUM" -> "alginate de sodium + bicarbonate de sodium"."""
    return re.sub(r"\s*//\s*|\s*/\s*", " + ", dci).lower()


def villes_txt(villes: list[str], langue: str) -> str:
    texte = ", ".join(villes[:MAX_VILLES])
    if len(villes) > MAX_VILLES:
        texte += t(langue, "et_autres", n=len(villes) - MAX_VILLES)
    return texte


def ligne_pharmacie(p: dict, langue: str) -> str:
    morceaux = [p["nom"]]
    if p.get("adresse"):
        adresse = p["adresse"]
        if p.get("ville") and p["ville"].lower() not in adresse.lower():
            adresse += f", {p['ville']}"
        morceaux.append(adresse)
    elif p.get("ville"):
        morceaux.append(p["ville"])
    if (tel := telephone_txt(p.get("telephone"))):
        morceaux.append(f"{t(langue, 'tel')} {tel}")
    if p.get("distance_km") is not None:
        morceaux.append(distance_txt(p["distance_km"], langue))
    if p.get("ouverture") == "24h":
        morceaux.append(t(langue, "ouverture_24h"))
    elif p.get("ouverture") == "nuit":
        morceaux.append(t(langue, "ouverture_nuit", horaires=p.get("horaires") or ""))
    return "- " + " — ".join(morceaux)


# --- Medicaments -----------------------------------------------------------------

def med_entete(resolu, langue: str) -> Bloc | None:
    """Une seule fois par medicament : introuvable, ou nom seulement approchant."""
    if resolu.statut == "introuvable":
        return phrase(langue, "med_introuvable", nom=resolu.cite.nom)
    if resolu.statut == "a_confirmer":
        return phrase(langue, "med_a_confirmer", nom=nom_txt(resolu.nom))
    return None


def dosage_absent(res: dict, langue: str) -> Bloc:
    return phrase(langue, "dosage_absent", nom=nom_txt(res.get("nom")),
                  dosage=str(res["dosage_absent"]).lower())


def _prix_par_dosage_txt(res: dict, langue: str) -> list[str]:
    lignes = []
    for d in res["par_dosage"]:
        prix = prix_txt(d["prix_min"], langue)
        if d["prix_max"] != d["prix_min"]:
            prix = t(langue, "prix_entre", min=prix, max=prix_txt(d["prix_max"], langue))
        lignes.append(f"- {str(d['dosage'] or '?').lower()} : {prix}")
    if res["dosages_coupes"]:
        lignes.append(t(langue, "formes_coupee"))
    return lignes


def composer_prix(res: dict, langue: str) -> Bloc:
    nom = nom_txt(res.get("nom"))
    if res["statut"] == "plus_commercialise":
        return phrase(langue, "med_plus_commercialise", nom=nom)
    if res["trop_de_presentations"]:
        if not res["par_dosage"]:
            return phrase(langue, "prix_inconnu", nom=nom)
        return Bloc([t(langue, "prix_par_dosage", nom=nom)] + _prix_par_dosage_txt(res, langue))
    lignes = [f"- {presentation_txt(p['dosage'], p['forme'])} : {prix_txt(p['ppv'], langue)}"
              for p in res["presentations"] if p["ppv"] is not None]
    if not lignes:
        return phrase(langue, "prix_inconnu", nom=nom)
    return Bloc([t(langue, "prix_tete", nom=nom)] + lignes)


def _remboursement_txt(r: dict | None, langue: str) -> str:
    if r is None:
        return t(langue, "remb_inconnu")
    if r["taux"] == 0:
        return t(langue, "remb_non")
    taux = nombre_txt(r["taux"], langue)
    if r["montant"] is not None and r["base"] is not None:
        return t(langue, "remb_montant", taux=taux, montant=prix_txt(r["montant"], langue),
                 base=prix_txt(r["base"], langue))
    return t(langue, "remb_taux", taux=taux)


def composer_remboursement(res: dict, regime: str, langue: str) -> Bloc:
    nom = nom_txt(res.get("nom"))
    if res["statut"] == "plus_commercialise":
        return phrase(langue, "med_plus_commercialise", nom=nom)
    if regime == "aucun":
        return phrase(langue, "remb_aucun", nom=nom)
    libelle = regime.upper()
    if res["trop_de_presentations"]:
        taux = res["taux_commun"].get(regime)
        if taux is None:
            return phrase(langue, "remb_variable", nom=nom, regime=libelle)
        if taux == 0:
            return phrase(langue, "remb_commun_non", nom=nom, regime=libelle)
        return phrase(langue, "remb_commun", nom=nom, regime=libelle, taux=nombre_txt(taux, langue))
    if not any(p[regime] for p in res["presentations"]):
        return phrase(langue, "remb_absent", nom=nom, regime=libelle)
    lignes = [f"- {presentation_txt(p['dosage'], p['forme'])} : {_remboursement_txt(p[regime], langue)}"
              for p in res["presentations"]]
    return Bloc([t(langue, "remb_tete", nom=nom, regime=libelle)] + lignes)


def composer_formes(res: dict, langue: str) -> Bloc:
    nom = nom_txt(res.get("nom"))
    if res["statut"] == "plus_commercialise":
        return phrase(langue, "med_plus_commercialise", nom=nom)
    tete = []
    if res.get("forme_demandee"):
        cle = "forme_existe" if res["forme_existe"] else "forme_absente"
        tete.append(t(langue, cle, nom=nom, forme=str(res["forme_demandee"]).lower()))
    lignes = [f"- {d['dosage'] or '?'} : {', '.join(f.lower() for f in d['formes'])}"
              for d in res["par_dosage"]]
    if res.get("liste_coupee"):
        lignes.append(t(langue, "formes_coupee"))
    return Bloc(tete + [t(langue, "formes_tete", nom=nom)] + lignes)


def composer_securite(res: dict, langue: str) -> Bloc:
    nom = nom_txt(res.get("nom"))
    if res["statut"] == "pas_d_info" and not res.get("manquantes"):
        return phrase(langue, "secu_absente", nom=nom)
    lignes = []
    for rubrique in res.get("rubriques", {}):
        lignes.append(t(langue, "secu_tete", rubrique=t(langue, f"rubrique_{rubrique}"), nom=nom))
        lignes.append(res["explications"].get(rubrique) or t(langue, "secu_sans_explication"))
    if res.get("manquantes"):
        rubriques = ", ".join(t(langue, f"rubrique_{r}").lower() for r in res["manquantes"])
        lignes.append(t(langue, "secu_rubrique_absente", nom=nom, rubriques=rubriques))
    return Bloc(lignes)


# --- Pharmacies ------------------------------------------------------------------

def composer_question_lieu(res: dict, langue: str) -> Bloc | None:
    """Les statuts qui demandent une precision sur le lieu, communs aux trois demandes."""
    if res["statut"] == "lieu_inconnu":
        if res.get("cite"):
            return phrase(langue, "ph_lieu_inconnu", lieu=res["cite"])
        return phrase(langue, "demander_lieu")
    if res["statut"] == "preciser_ville":
        return phrase(langue, "ph_preciser_ville", lieu=res.get("lieu") or res.get("nom"),
                      villes=villes_txt(res["villes"], langue))
    return None


def composer_pharmacies_lieu(res: dict, langue: str) -> Bloc:
    if (question := composer_question_lieu(res, langue)):
        return question
    if res["statut"] == "preciser_quartier":
        tete = []
        if res.get("quartier_inconnu"):
            tete.append(t(langue, "ph_quartier_inconnu", quartier=res["quartier_inconnu"], ville=res["ville"]))
        tete.append(t(langue, "ph_preciser_quartier", n=res["nb_pharmacies"], ville=res["ville"]))
        return Bloc(tete)
    lignes = [ligne_pharmacie(p, langue) for p in res["pharmacies"]]
    if res["lieu"] == res["ville"]:
        tete = []
        if res.get("quartier_inconnu"):
            tete.append(t(langue, "ph_quartier_inconnu", quartier=res["quartier_inconnu"], ville=res["ville"]))
        return Bloc(tete + [t(langue, "ph_ville", ville=res["ville"])], lignes)
    pied = [t(langue, "ph_approx")] if res.get("source_lieu") == "adresses" else []
    return Bloc([t(langue, "ph_proches", lieu=res["lieu"], ville=res["ville"])], lignes, pied)


def composer_garde(res: dict, langue: str) -> Bloc:
    if (question := composer_question_lieu(res, langue)):
        return question
    if res["statut"] == "aucune":
        return Bloc([t(langue, "garde_aucune", ville=res["ville"]), t(langue, "garde_aveu")])
    lignes = [ligne_pharmacie(p, langue) for p in res["pharmacies"]]
    return Bloc([t(langue, "garde_tete", ville=res["ville"])], lignes, [t(langue, "garde_aveu")])


def composer_info_pharmacie(res: dict, langue: str, lieu_cite: str | None = None) -> Bloc:
    if res["statut"] == "preciser_ville":
        return phrase(langue, "ph_preciser_ville", lieu=res.get("nom") or res.get("lieu"),
                      villes=villes_txt(res["villes"], langue))
    pied = [t(langue, "info_lieu_inconnu", lieu=lieu_cite)] if res.get("lieu_inconnu") and lieu_cite else []
    if res["statut"] == "introuvable":
        if res.get("ville"):
            return Bloc([t(langue, "info_introuvable_ville", nom=res["cite"], ville=res["ville"])], [], pied)
        return Bloc([t(langue, "info_introuvable", nom=res["cite"])], [], pied)
    pharmacies = res["pharmacies"]
    lignes = [ligne_pharmacie(p, langue) for p in pharmacies]
    if res["statut"] == "a_confirmer":
        tete = [t(langue, "info_a_confirmer", nom=res["nom"])]
    elif res["nb_trouvees"] > 1:
        tete = [t(langue, "info_plusieurs", n=res["nb_trouvees"], ville=pharmacies[0]["ville"])]
    else:
        tete = []
    # Une seule pharmacie : sa ligne EST la reponse, elle reste dans la version courte.
    if len(lignes) == 1 and not tete:
        return Bloc(lignes, [], pied)
    return Bloc(tete, lignes, pied)


# --- Conseil symptomes ---------------------------------------------------------------

def composer_conseil(res: dict, langue: str) -> Bloc:
    if res["statut"] == "professionnel":
        return phrase(langue, f"conseil_{res['raison']}")
    lignes, signes = [], []
    for s in res["symptomes"]:
        if s["statut"] == "inconnu":
            lignes.append(t(langue, "conseil_inconnu"))
            continue
        symptome = s["libelles"].get(langue) or s["libelles"]["fr"]
        dans_phrase = minuscule_initiale(symptome) if langue == "fr" else symptome
        pro = t(langue, f"pro_{s['orientation'].lower()}")
        duree = duree_txt(s["duree_max_jours"], langue)
        if s["statut"] == "trop_long":
            lignes.append(t(langue, "conseil_trop_long", symptome=symptome, duree=duree))
            continue
        if s["statut"] == "orientation":
            lignes.append(t(langue, "conseil_orientation", symptome=dans_phrase, pro=pro))
        else:
            molecules = t(langue, "ou").join(molecule_txt(m) for m in s["molecules"])
            lignes.append(t(langue, "conseil_molecule", symptome=dans_phrase, molecules=molecules,
                            duree=duree))
            if s["orientation"] != "PHARMACIEN":
                lignes.append(t(langue, "conseil_fin", pro=pro))
        signes += [x for x in s.get("signes_alerte", []) if x not in signes]
    if signes:
        # Les signes d'alerte de la liste sont ecrits en francais : dans les
        # autres langues, la phrase est generale. Une seule fois, a la fin.
        lignes.append(t(langue, "conseil_alerte", signes=", ".join(signes)))
    return Bloc(lignes)
