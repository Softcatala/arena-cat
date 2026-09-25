"""Qüestionari configurable i acreditació dels avaluadors."""

from pathlib import Path
from typing import Self

import yaml
from fastapi import HTTPException
from pydantic import model_validator
from sqlalchemy import func, update
from sqlalchemy.orm import Session

from app.models import User
from app.schemas import (
    QualificationChoice,
    QualificationQuestion,
    QualificationRequest,
    QualificationResponse,
    QualificationResult,
)

QUALIFICATION_FILE = Path(__file__).resolve().parents[3] / "data/qualification.yaml"


class Question(QualificationQuestion):
    correct_answer: QualificationChoice
    explanation: str


class Questionnaire(QualificationResponse):
    questions: list[Question]

    @model_validator(mode="after")
    def validate_questions(self) -> Self:
        ids = {question.id for question in self.questions}
        if len(ids) != len(self.questions) or not 1 <= self.min_correct <= len(ids):
            raise ValueError("Els identificadors han de ser únics i el llindar ha de ser assolible")
        return self


def load_qualification() -> Questionnaire:
    """Llegeix el YAML perquè els canvis de preguntes o llindar siguin efectius."""
    return Questionnaire.model_validate(
        yaml.safe_load(QUALIFICATION_FILE.read_text(encoding="utf-8"))
    )


def submit_qualification(
    db: Session, user: User, payload: QualificationRequest, *, debug: bool = False
) -> QualificationResult:
    """Corregeix un intent complet i desa només la primera acreditació."""
    if user.qualified_at is not None:
        raise HTTPException(status_code=409, detail="Ja heu superat la prova")

    questionnaire = load_qualification()
    score = 0
    if not debug:
        if set(payload.answers) != {question.id for question in questionnaire.questions}:
            raise HTTPException(
                status_code=422, detail="Cal respondre totes les preguntes de la prova"
            )
        score = sum(
            payload.answers[question.id] == question.correct_answer
            for question in questionnaire.questions
        )
    passed = debug or score >= questionnaire.min_correct
    if passed:
        db.execute(
            update(User)
            .where(User.id == user.id, User.qualified_at.is_(None))
            .values(qualified_at=func.now())
        )
        db.commit()

    return QualificationResult(
        score=score,
        total=len(questionnaire.questions),
        min_correct=questionnaire.min_correct,
        passed=passed,
    )
