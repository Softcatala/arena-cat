"""Biblioteca de rànquing i selecció de parelles per a Arena Cat (tasca #7).

Tres funcions públiques, una per pregunta de la tasca:

- `select_next_task(session, category_code)`:
      Quina és la propera parella de models a avaluar per a l'usuari?
- `compute_ranking(session, category_code)`:
      Quin és el rànquing actual dels models?
- `assess_confidence(session, category_code)`:
      Quina confiança tenim en el rànquing actual?

Totes les funcions accepten una sessió SQLAlchemy oberta i un codi de
categoria. Retornen diccionaris serialitzables a JSON; la microservei
(tasca #6) els passa directament als endpoints de FastAPI.
"""

from app.ranking.confidence import assess_confidence
from app.ranking.ranking import compute_ranking
from app.ranking.sampler import select_next_task

__all__ = ["assess_confidence", "compute_ranking", "select_next_task"]
