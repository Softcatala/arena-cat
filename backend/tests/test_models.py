"""Tests del model de dades: relacions, unicitat, enums, restricció CHECK i índexs."""

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.models import CategoriaTasca, Guanyador, Prompt, Resposta, Vot


def _prompt_amb_respostes(session):
    """Crea un prompt amb dues respostes de models diferents i retorna (p, ra, rb)."""
    prompt = Prompt(
        versio="v1",
        codi="traduccio-01",
        categoria=CategoriaTasca.traduccio,
        text="Tradueix aquest text al català en registre col·loquial.",
    )
    resposta_a = Resposta(prompt=prompt, model="salamandra-7b", text="Resposta del model A")
    resposta_b = Resposta(prompt=prompt, model="qwen-3.5-9b", text="Resposta del model B")
    session.add(prompt)
    session.flush()
    return prompt, resposta_a, resposta_b


def test_crear_prompt_resposta_vot(session):
    prompt, resposta_a, resposta_b = _prompt_amb_respostes(session)

    vot = Vot(
        prompt=prompt,
        resposta_a_id=resposta_a.id,
        resposta_b_id=resposta_b.id,
        guanyador=Guanyador.a,
        sessio_id="sessio-anonima-123",
        temps_resposta_s=12.5,
    )
    session.add(vot)
    session.flush()

    assert vot.id is not None
    # Navegació de relacions.
    assert len(prompt.respostes) == 2
    assert resposta_a.prompt is prompt


def test_metadades_jsonb(session):
    prompt, _, _ = _prompt_amb_respostes(session)
    resposta = Resposta(
        prompt=prompt,
        model="gemma-4-26b",
        text="Una resposta amb metadades",
        metadades={"seed": 42, "temperatura": 0.7, "top_p": 0.95, "quantization": "int4"},
    )
    session.add(resposta)
    session.flush()
    session.refresh(resposta)
    assert resposta.metadades["seed"] == 42


def test_resposta_unica_per_prompt_i_model(session):
    prompt, _, _ = _prompt_amb_respostes(session)
    # Mateix prompt + mateix model que la resposta A ja existent → viola UNIQUE.
    session.add(Resposta(prompt=prompt, model="salamandra-7b", text="Duplicada"))
    with pytest.raises(IntegrityError):
        session.flush()


def test_prompt_unic_per_versio_i_codi(session):
    _prompt_amb_respostes(session)
    session.add(
        Prompt(
            versio="v1",
            codi="traduccio-01",
            categoria=CategoriaTasca.correccio,
            text="Un altre text amb el mateix codi i versió",
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.parametrize("valor", list(Guanyador))
def test_guanyador_accepta_valors_valids(session, valor):
    prompt, resposta_a, resposta_b = _prompt_amb_respostes(session)
    vot = Vot(
        prompt=prompt,
        resposta_a_id=resposta_a.id,
        resposta_b_id=resposta_b.id,
        guanyador=valor,
    )
    session.add(vot)
    session.flush()
    assert vot.guanyador is valor


def test_guanyador_rebutja_valor_invalid(session):
    prompt, resposta_a, resposta_b = _prompt_amb_respostes(session)
    # Inserció directa amb un valor fora de l'enum: la base de dades l'ha de rebutjar.
    with pytest.raises(DBAPIError):
        session.execute(
            text(
                "INSERT INTO vots (prompt_id, resposta_a_id, resposta_b_id, guanyador) "
                "VALUES (:p, :a, :b, 'guanyador_inexistent')"
            ),
            {"p": prompt.id, "a": resposta_a.id, "b": resposta_b.id},
        )


def test_categoria_rebutja_valor_invalid(session):
    with pytest.raises(DBAPIError):
        session.execute(
            text(
                "INSERT INTO prompts (versio, codi, categoria, text) "
                "VALUES ('v1', 'x-01', 'categoria_inexistent', 'text')"
            )
        )


def test_vot_amb_respostes_iguals_es_rebutjat(session):
    prompt, resposta_a, _ = _prompt_amb_respostes(session)
    vot = Vot(
        prompt=prompt,
        resposta_a_id=resposta_a.id,
        resposta_b_id=resposta_a.id,  # mateixa resposta a A i B → viola el CHECK
        guanyador=Guanyador.empat,
    )
    session.add(vot)
    with pytest.raises(IntegrityError):
        session.flush()


def test_indexs_de_vots(engine):
    noms = {idx["name"] for idx in inspect(engine).get_indexes("vots")}
    assert "ix_vots_prompt_id" in noms
    assert "ix_vots_creat_a" in noms


def test_creat_a_s_omple_automaticament(session):
    prompt, _, _ = _prompt_amb_respostes(session)
    session.refresh(prompt)
    assert prompt.creat_a is not None
    assert prompt.creat_a.tzinfo is not None  # és timestamptz
