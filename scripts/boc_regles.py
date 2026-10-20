"""Règles de lecture des bulletins officiels de la cote (BRVM) partagées par la construction du terminal (build_terminal.py) et
l'archive des bulletins (histo.py) : une seule règle, appliquée de la même façon des deux côtés.
Bibliothèque standard Python uniquement."""


def cours_moyen_ok(vol, val, *cours):
    """Montant échangé vraisemblable : cours moyen (montant ÷ volume) compris entre 85 % du plus bas et 115 % du plus haut des
    cours connus de la séance (clôture, ouverture, cours précédent). Toutes les transactions d'une séance se font à ±7,5 % du
    cours de référence : le cours moyen ne peut pas s'en écarter davantage (marge comprise pour les arrondis)."""
    try:
        px = [float(x) for x in cours if x and float(x) > 0]
        if not (vol and val and px and float(vol) > 0 and float(val) > 0):
            return False
        a = float(val) / float(vol)
        return min(px) * .85 <= a <= max(px) * 1.15
    except (TypeError, ValueError, ZeroDivisionError):
        return False


def milliers(vol, val, *cours):
    """Nombres imprimés en milliers dans certains bulletins (dernier groupe de trois chiffres absent : Sonatel en 2026, montants
    d'un milliard et plus ; ETI le 17/09/2026, volume de plus de dix millions de titres). Renvoie (volume, montant, quoi) :
    quoi = None (rien de changé), « val » (montant × 1 000) ou « vol » (volume × 1 000). La correction n'est faite que si le
    nombre rétabli redonne un cours moyen vraisemblable (cours_moyen_ok) alors que le nombre lu ne le fait pas, et seulement
    pour les grands nombres (montant rétabli d'au moins un milliard, volume d'au moins dix millions) : un facteur 1 000 sépare
    les deux lectures, aucune ligne ne peut être vraisemblable des deux façons."""
    if cours_moyen_ok(vol, val, *cours):
        return vol, val, None
    try:
        if vol and val and float(val) * 1000 >= 1e9 and cours_moyen_ok(vol, float(val) * 1000, *cours):
            return vol, float(val) * 1000, "val"
        if vol and val and float(vol) * 1000 >= 1e7 and cours_moyen_ok(float(vol) * 1000, val, *cours):
            return float(vol) * 1000, val, "vol"
    except (TypeError, ValueError):
        pass
    return vol, val, None
